// ADAPTATION: ABI v1, robust process-shared locking and bounded acquisition.
#pragma once
#include <cstdint>
#include <cstddef>
#include <pthread.h>
namespace flash {
constexpr uint64_t MAGIC=0x464c4153484d3201ULL;
constexpr uint32_t ABI=1;
struct Event {
  uint64_t publish_seq, call_seq, timestamp_ns, thread_id, comm_ptr, comm_generation;
  uint64_t count, group_id, stream_ptr, checksum;
  int32_t api, result, global_rank, comm_rank, comm_size, datatype, op, peer;
  uint32_t group_depth, identity;
  char id_hash[65];
  uint8_t reserved[7];
};
static_assert(sizeof(Event)==192);
struct Header {
  uint32_t ready, abi;
  uint64_t magic, mapping_bytes;
  uint32_t header_bytes, event_bytes, capacity, state;
  int32_t writer_pid, global_rank;
  uint64_t created_ns, write_pos, read_pos;
  uint64_t attempts, dropped_full, dropped_lock, errors, bad_records;
  uint32_t closed, poisoned;
  char run_id[81], node_id[33];
  pthread_mutex_t mutex;
};
struct Handle { Header* h; Event* events; size_t bytes; int fd; bool reader; };
uint64_t now_ns();
uint64_t checksum(const Event&);
Handle* create(const char*,const char*,const char*,int,uint32_t);
Handle* open_reader(const char*,const char*,const char*);
int emit(Handle*,Event);
int read(Handle*,Event&);
int acknowledge(Handle*,uint64_t);
int snapshot(Handle*,char*,size_t);
void close_handle(Handle*);
int unlink_run(const char*,const char*,const char*);
}
extern "C" {
void* flash_ring_create(const char*,const char*,const char*,int,uint32_t);
void* flash_ring_open(const char*,const char*,const char*);
int flash_ring_read(void*,char*,size_t);
int flash_ring_ack(void*,uint64_t);
int flash_ring_snapshot(void*,char*,size_t);
void flash_ring_close(void*);
int flash_ring_unlink(const char*,const char*,const char*);
}
