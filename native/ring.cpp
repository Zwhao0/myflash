// PAPER: chapter 3 §3.3.1 ring; ADAPTATION: all shared mutations under robust mutex.
// No Python direct access to shared memory, no CUDA APIs in this component.
#include "ring.hpp"
#include <sys/mman.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <unistd.h>
#include <signal.h>
#include <fcntl.h>
#include <cerrno>
#include <cstring>
#include <cstdio>
#include <ctime>
#include <string>
#include <sstream>
#include <new>
namespace flash {
uint64_t now_ns() { timespec t{}; clock_gettime(CLOCK_MONOTONIC,&t); return uint64_t(t.tv_sec)*1000000000ULL+t.tv_nsec; }
uint64_t checksum(const Event& value) {
  Event e=value; e.checksum=0;
  uint64_t hash=14695981039346656037ULL;
  auto bytes=reinterpret_cast<const unsigned char*>(&e);
  for(size_t i=0;i<sizeof(e);++i) {hash^=bytes[i];hash*=1099511628211ULL;}
  return hash;
}
static bool valid(const char* s,size_t max) {
  if(!s || !*s || strlen(s)>max) return false;
  for(auto p=s;*p;++p) if(!((*p>='a'&&*p<='z')||(*p>='A'&&*p<='Z')||(*p>='0'&&*p<='9')||*p=='_'||*p=='-')) return false;
  return true;
}
static bool name_ok(const char* name) {
  return name && strncmp(name,"/flash_m2_",10)==0 && valid(name+1,240);
}
static int lock(Header* h) {
  timespec deadline{};clock_gettime(CLOCK_MONOTONIC,&deadline);
  deadline.tv_nsec+=10000000; if(deadline.tv_nsec>=1000000000){++deadline.tv_sec;deadline.tv_nsec-=1000000000;}
  int rc=pthread_mutex_clocklock(&h->mutex,CLOCK_MONOTONIC,&deadline);
  if(rc==EOWNERDEAD) {
    h->poisoned=1; __atomic_fetch_add(&h->errors,1ULL,__ATOMIC_RELAXED);
    pthread_mutex_consistent(&h->mutex); pthread_mutex_unlock(&h->mutex); return -EIO;
  }
  if(rc) return -rc;
  if(h->poisoned){pthread_mutex_unlock(&h->mutex);return -EIO;}
  return 0;
}
Handle* create(const char* name,const char* run,const char* node,int rank,uint32_t cap) {
  if(!name_ok(name)||!valid(run,80)||!valid(node,32)||cap<1||cap>1048576){errno=EINVAL;return nullptr;}
  int fd=shm_open(name,O_CREAT|O_EXCL|O_RDWR|O_CLOEXEC,0600);if(fd<0)return nullptr;
  size_t bytes=sizeof(Header)+size_t(cap)*sizeof(Event);
  if(ftruncate(fd,bytes)){int error=errno;::close(fd);shm_unlink(name);errno=error;return nullptr;}
  int allocation=posix_fallocate(fd,0,bytes);
  if(allocation){::close(fd);shm_unlink(name);errno=allocation;return nullptr;}
  void* p=mmap(nullptr,bytes,PROT_READ|PROT_WRITE,MAP_SHARED,fd,0);
  if(p==MAP_FAILED){int error=errno;::close(fd);shm_unlink(name);errno=error;return nullptr;}
  auto h=static_cast<Header*>(p); // O_EXCL + ftruncate provides a fresh zero-filled mapping; ready is only atomically published.
  pthread_mutexattr_t attr;int rc=pthread_mutexattr_init(&attr);
  if(!rc)rc=pthread_mutexattr_setpshared(&attr,PTHREAD_PROCESS_SHARED);
  if(!rc)rc=pthread_mutexattr_setrobust(&attr,PTHREAD_MUTEX_ROBUST);
  if(!rc)rc=pthread_mutex_init(&h->mutex,&attr);
  pthread_mutexattr_destroy(&attr);
  if(rc){munmap(p,bytes);::close(fd);shm_unlink(name);errno=rc;return nullptr;}
  h->abi=ABI;h->magic=MAGIC;h->mapping_bytes=bytes;h->header_bytes=sizeof(Header);h->event_bytes=sizeof(Event);
  h->capacity=cap;h->writer_pid=getpid();h->global_rank=rank;h->created_ns=now_ns();
  strcpy(h->run_id,run);strcpy(h->node_id,node);h->state=0;
  __atomic_store_n(&h->ready,1U,__ATOMIC_RELEASE);
  return new Handle{h,reinterpret_cast<Event*>(static_cast<char*>(p)+sizeof(Header)),bytes,fd,false};
}
Handle* open_reader(const char* name,const char* run,const char* node) {
  if(!name_ok(name)||!valid(run,80)||!valid(node,32)){errno=EINVAL;return nullptr;}
  int fd=shm_open(name,O_RDWR|O_CLOEXEC,0);if(fd<0)return nullptr;
  if(flock(fd,LOCK_EX|LOCK_NB)){int error=errno;::close(fd);errno=error;return nullptr;}
  struct stat st{};
  if(fstat(fd,&st)||st.st_uid!=getuid()){::close(fd);errno=EPROTO;return nullptr;}
  if(st.st_size==0){::close(fd);errno=EAGAIN;return nullptr;}
  if(st.st_size<off_t(sizeof(Header))){::close(fd);errno=EPROTO;return nullptr;}
  size_t bytes=st.st_size;void* p=mmap(nullptr,bytes,PROT_READ|PROT_WRITE,MAP_SHARED,fd,0);
  if(p==MAP_FAILED){int error=errno;::close(fd);errno=error;return nullptr;}
  auto h=static_cast<Header*>(p);
  bool ready=__atomic_load_n(&h->ready,__ATOMIC_ACQUIRE)==1;
  bool good=ready && h->magic==MAGIC && h->abi==ABI && h->header_bytes==sizeof(Header) && h->event_bytes==sizeof(Event)
    && h->capacity>=1 && h->capacity<=1048576 && h->mapping_bytes==bytes
    && bytes==sizeof(Header)+size_t(h->capacity)*sizeof(Event)
    && memchr(h->run_id,0,sizeof(h->run_id)) && memchr(h->node_id,0,sizeof(h->node_id))
    && strcmp(h->run_id,run)==0 && strcmp(h->node_id,node)==0;
  if(!good){munmap(p,bytes);::close(fd);errno=ready?EPROTO:EAGAIN;return nullptr;}
  return new Handle{h,reinterpret_cast<Event*>(static_cast<char*>(p)+sizeof(Header)),bytes,fd,true};
}
int emit(Handle* handle,Event e) {
  if(!handle||handle->reader)return -EINVAL;
  auto h=handle->h;__atomic_fetch_add(&h->attempts,1ULL,__ATOMIC_RELAXED);
  int rc=lock(h);
  if(rc){__atomic_fetch_add(&h->dropped_lock,1ULL,__ATOMIC_RELAXED);return rc;}
  if(h->closed || h->state!=0 || h->write_pos<h->read_pos || h->write_pos-h->read_pos>h->capacity) {
    __atomic_fetch_add(&h->errors,1ULL,__ATOMIC_RELAXED);pthread_mutex_unlock(&h->mutex);return -EIO;
  }
  if(h->write_pos-h->read_pos==h->capacity) {
    __atomic_fetch_add(&h->dropped_full,1ULL,__ATOMIC_RELAXED);pthread_mutex_unlock(&h->mutex);return -ENOSPC;
  }
  e.publish_seq=h->write_pos+1;e.checksum=checksum(e);
  handle->events[h->write_pos%h->capacity]=e;
  ++h->write_pos; // unlock publishes the entire slot before the consumer can read.
  pthread_mutex_unlock(&h->mutex);return 0;
}
int read(Handle* handle,Event& e) {
  if(!handle||!handle->reader)return -EINVAL;
  auto h=handle->h;int rc=lock(h);if(rc)return rc;
  if(h->state!=0||h->write_pos<h->read_pos||h->write_pos-h->read_pos>h->capacity) {
    __atomic_fetch_add(&h->errors,1ULL,__ATOMIC_RELAXED);pthread_mutex_unlock(&h->mutex);return -EPROTO;
  }
  if(h->read_pos==h->write_pos){pthread_mutex_unlock(&h->mutex);return 0;}
  e=handle->events[h->read_pos%h->capacity];
  bool good=e.publish_seq==h->read_pos+1 && e.checksum==checksum(e) && e.id_hash[64]==0 && e.global_rank==h->global_rank;
  if(!good)++h->read_pos;
  if(!good){++h->bad_records;__atomic_fetch_add(&h->errors,1ULL,__ATOMIC_RELAXED);}
  pthread_mutex_unlock(&h->mutex);return good?1:-EBADMSG;
}
int acknowledge(Handle* handle,uint64_t seq) {
  if(!handle||!handle->reader)return -EINVAL;
  auto h=handle->h;int rc=lock(h);if(rc)return rc;
  if(h->read_pos==h->write_pos||seq!=h->read_pos+1)rc=-EINVAL;
  else ++h->read_pos;
  pthread_mutex_unlock(&h->mutex);return rc;
}
static int copy_string(const std::string& s,char* out,size_t n) {
  if(!out||n<=s.size())return -ENOBUFS;
  memcpy(out,s.c_str(),s.size()+1);return 0;
}
int snapshot(Handle* handle,char* out,size_t n) {
  if(!handle)return -EINVAL;auto h=handle->h;
  int rc=lock(h);if(rc)return rc;
  std::ostringstream s;
  s<<"{\"abi\":"<<h->abi<<",\"capacity\":"<<h->capacity<<",\"event_bytes\":"<<h->event_bytes
   <<",\"state\":"<<h->state<<",\"pid\":"<<h->writer_pid<<",\"global_rank\":"<<h->global_rank
   <<",\"run_id\":\""<<h->run_id<<"\",\"node_id\":\""<<h->node_id<<"\",\"created_ns\":"<<h->created_ns
   <<",\"write_pos\":"<<h->write_pos<<",\"read_pos\":"<<h->read_pos<<",\"attempts\":"<<__atomic_load_n(&h->attempts,__ATOMIC_RELAXED)
   <<",\"dropped_full\":"<<__atomic_load_n(&h->dropped_full,__ATOMIC_RELAXED)<<",\"dropped_lock\":"<<__atomic_load_n(&h->dropped_lock,__ATOMIC_RELAXED)
   <<",\"errors\":"<<__atomic_load_n(&h->errors,__ATOMIC_RELAXED)<<",\"bad_records\":"<<h->bad_records
   <<",\"closed\":"<<h->closed<<",\"poisoned\":"<<h->poisoned<<"}";
  pthread_mutex_unlock(&h->mutex);return copy_string(s.str(),out,n);
}
void close_handle(Handle* handle) {
  if(!handle)return;
  if(!handle->reader) {
    int rc=lock(handle->h);
    if(!rc){handle->h->closed=1;pthread_mutex_unlock(&handle->h->mutex);}
  }
  munmap(handle->h,handle->bytes);::close(handle->fd);delete handle;
}
int unlink_run(const char* name,const char* run,const char* node) {
  auto handle=open_reader(name,run,node);if(!handle)return -errno;
  auto h=handle->h;int rc=lock(h);
  if(!rc) {
    bool dead=kill(h->writer_pid,0)==-1&&errno==ESRCH;
    if((!h->closed&&!dead)||h->read_pos!=h->write_pos)rc=-EBUSY;
    pthread_mutex_unlock(&h->mutex);
  }
  // Poisoned data must be explicitly accounted by the operator; no automatic unlink.
  if(!rc && shm_unlink(name))rc=-errno;
  close_handle(handle);return rc;
}
}
extern "C" {
void* flash_ring_create(const char* n,const char* r,const char* d,int rank,uint32_t cap){return flash::create(n,r,d,rank,cap);}
void* flash_ring_open(const char* n,const char* r,const char* d){return flash::open_reader(n,r,d);}
int flash_ring_ack(void* h,uint64_t seq){return flash::acknowledge(static_cast<flash::Handle*>(h),seq);}
int flash_ring_snapshot(void* h,char* b,size_t n){return flash::snapshot(static_cast<flash::Handle*>(h),b,n);}
void flash_ring_close(void* h){flash::close_handle(static_cast<flash::Handle*>(h));}
int flash_ring_unlink(const char* n,const char* r,const char* d){return flash::unlink_run(n,r,d);}
int flash_ring_read(void* handle,char* out,size_t n) {
  // Fixed output capacity checked before advancing the shared cursor.
  if(!out||n<4096)return -ENOBUFS;
  flash::Event e{};int rc=flash::read(static_cast<flash::Handle*>(handle),e);if(rc!=1)return rc;
  std::ostringstream s;
  s<<"{\"publish_seq\":"<<e.publish_seq<<",\"call_seq\":"<<e.call_seq<<",\"timestamp_ns\":"<<e.timestamp_ns
   <<",\"thread_id\":"<<e.thread_id<<",\"comm_ptr\":"<<e.comm_ptr<<",\"comm_generation\":"<<e.comm_generation
   <<",\"count\":"<<e.count<<",\"group_id\":"<<e.group_id<<",\"stream_ptr\":"<<e.stream_ptr
   <<",\"api\":"<<e.api<<",\"result\":"<<e.result<<",\"global_rank\":"<<e.global_rank
   <<",\"comm_rank\":"<<e.comm_rank<<",\"comm_size\":"<<e.comm_size<<",\"datatype\":"<<e.datatype
   <<",\"op\":"<<e.op<<",\"peer\":"<<e.peer<<",\"group_depth\":"<<e.group_depth
   <<",\"identity\":"<<e.identity<<",\"id_hash\":\""<<e.id_hash<<"\"}";
  auto value=s.str();if(value.size()+1>n)return -ENOBUFS;
  memcpy(out,value.c_str(),value.size()+1);return 1;
}
#ifdef FLASH_RING_TESTING
int flash_test_lock(void* handle){return pthread_mutex_lock(&static_cast<flash::Handle*>(handle)->h->mutex);}
int flash_test_unlock(void* handle){return pthread_mutex_unlock(&static_cast<flash::Handle*>(handle)->h->mutex);}
int flash_test_write(void* handle,uint64_t count,int dtype) {
  auto h=static_cast<flash::Handle*>(handle);flash::Event e{};
  static uint64_t test_calls=0;e.call_seq=__atomic_add_fetch(&test_calls,1ULL,__ATOMIC_RELAXED);e.count=count;e.datatype=dtype;e.global_rank=h->h->global_rank;e.api=1;e.timestamp_ns=flash::now_ns();
  return flash::emit(h,e);
}
int flash_test_corrupt(void* handle,int what) {
  auto h=static_cast<flash::Handle*>(handle);
  int rc=pthread_mutex_lock(&h->h->mutex);if(rc)return -rc;
  if(what==0)h->events[h->h->read_pos%h->h->capacity].count^=1;
  if(what==1)h->h->abi=999;
  pthread_mutex_unlock(&h->h->mutex);return 0;
}
void flash_test_owner_die(void* handle) {
  auto h=static_cast<flash::Handle*>(handle);pthread_mutex_lock(&h->h->mutex);_exit(0);
}
#endif
}
