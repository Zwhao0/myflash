// PAPER §3.2.1/3.3.1: LD_PRELOAD, lazy Monitor-only metadata.
// UPSTREAM signatures: installed NCCL 2.27.3 nccl.h. Independent implementation.
// ADAPTATION: SHA256 unique-id, thread-local Group scope, explicit unresolved identities.
#include <nccl.h>
#include <openssl/sha.h>
#include "ring.hpp"
#include <dlfcn.h>
#include <sys/syscall.h>
#include <unistd.h>
#include <atomic>
#include <mutex>
#include <unordered_map>
#include <vector>
#include <cstdlib>
#include <cstdio>
#include <cstring>
#include <climits>
#include <cerrno>
#include <cmath>
namespace {
enum API { AllReduce=1,AllGather=2,Broadcast=3,Bcast=4,Reduce=5,ReduceScatter=6,Send=7,Recv=8,
 InitRank=10,InitConfig=11,Split=12,InitAll=13,InitScalable=14,
 GroupStart=20,GroupEnd=21,GroupSimulateEnd=22,Finalize=30,Destroy=31,Abort=32,
 GetAsyncError=40,CommCount=41,CommUserRank=42,GetUniqueId=43,GetVersion=44,
 Register=45,Deregister=46,MemAlloc=47,MemFree=48,RedOpCreate=49,RedOpDestroy=50,Mapping=100 };
enum Identity { UNKNOWN=0,UNIQUE_ID_SHA256=1,UNRESOLVED_SPLIT=2,PENDING_GROUP=3,UNSUPPORTED_INIT=4 };
struct Comm {uint64_t generation=0;int rank=-1,size=-1;uint32_t identity=UNKNOWN;char hash[65]{};};
struct Pending {ncclComm_t* output;Comm info;flash::Event source;};
thread_local unsigned group_depth=0;
thread_local uint64_t group_id=0;
thread_local uint64_t control=0;
thread_local bool inside=false;
thread_local std::vector<Pending> pending;
std::atomic<uint64_t> calls{0},groups{0},generations{0};
struct Runtime {
 std::mutex mutex;std::unordered_map<uintptr_t,Comm> comms;flash::Handle* handle=nullptr;
 int rank=-1;bool disabled=false;
 Runtime() {
   const char* run=getenv("FLASH_RUN_ID");const char* node=getenv("FLASH_NODE_ID");const char* r=getenv("RANK");
   if(!run||!node||!r){disabled=true;return;}
   char* end=nullptr;long value=strtol(r,&end,10);
   if(!*r||*end||value<0||value>INT_MAX){disabled=true;return;}rank=value;
   uint32_t cap=8192;
   if(const char* c=getenv("FLASH_RING_CAPACITY")) {long v=strtol(c,&end,10);if(!*c||*end||v<1||v>1048576){disabled=true;return;}cap=v;}
   char name[241];int n=snprintf(name,sizeof(name),"/flash_m2_%s_%s_%d_%llu",run,node,getpid(),(unsigned long long)flash::now_ns());
   if(n<0||size_t(n)>=sizeof(name)){disabled=true;return;}
   handle=flash::create(name,run,node,rank,cap);
   if(!handle){disabled=true;fprintf(stderr,"FLASH_PROBE_SHM_ERROR errno=%d\n",errno);return;}
   fprintf(stderr,"FLASH_PROBE_READY name=%s abi=%u rank=%d\n",name,flash::ABI,rank);
 }
};
Runtime& runtime(){static Runtime* p=new Runtime;return *p;}
void shutdown_probe(){auto& r=runtime();std::lock_guard<std::mutex> lock(r.mutex);flash::close_handle(r.handle);r.handle=nullptr;r.disabled=true;}
Runtime& active_runtime(){auto& r=runtime();static bool registered=(atexit(shutdown_probe)==0);(void)registered;return r;}
void sha_id(ncclUniqueId id,Comm& info) {
 unsigned char digest[SHA256_DIGEST_LENGTH];SHA256(reinterpret_cast<unsigned char*>(id.internal),sizeof(id.internal),digest);
 for(size_t i=0;i<sizeof(digest);++i)snprintf(info.hash+2*i,3,"%02x",digest[i]);
 info.identity=UNIQUE_ID_SHA256;
}
struct Guard {bool outer;Guard():outer(!inside){inside=true;}~Guard(){if(outer)inside=false;}};
void associate(flash::Event& e,ncclComm_t comm) {
 e.comm_ptr=reinterpret_cast<uintptr_t>(comm);
 if(!comm)return;
 auto& r=active_runtime();std::lock_guard<std::mutex> lock(r.mutex);
 auto it=r.comms.find(e.comm_ptr);if(it!=r.comms.end()){
  auto& c=it->second;e.comm_generation=c.generation;e.comm_rank=c.rank;e.comm_size=c.size;e.identity=c.identity;memcpy(e.id_hash,c.hash,65);
 }
}
flash::Event event(int api,ncclComm_t comm=nullptr) {
 flash::Event e{};e.api=api;e.call_seq=++calls;e.timestamp_ns=flash::now_ns();e.thread_id=syscall(SYS_gettid);
 e.state=control&1;e.profile_epoch=control>>1;
 e.group_id=group_id;e.group_depth=group_depth;e.datatype=e.op=e.peer=e.comm_rank=e.comm_size=-1;
 auto& r=active_runtime();e.global_rank=r.rank;associate(e,comm);return e;
}
void record(flash::Event e,ncclResult_t result) noexcept {
 try {auto& r=active_runtime();e.result=result;if(r.handle)flash::emit(r.handle,e);}
 catch(...) {fprintf(stderr,"FLASH_PROBE_METADATA_ERROR\n");}
}
void add(ncclComm_t comm,Comm info) {
 if(!comm)return;info.generation=++generations;auto& r=active_runtime();
 std::lock_guard<std::mutex> lock(r.mutex);r.comms[reinterpret_cast<uintptr_t>(comm)]=info;
}
void map_pending(ncclComm_t* output,Comm info,flash::Event source,ncclResult_t rc) {
 if(rc!=ncclSuccess||!output)return;
 if(group_depth){pending.push_back({output,info,source});return;}
 if(*output)add(*output,info);
}
void finish_pending(ncclResult_t rc) {
 if(rc==ncclSuccess)for(auto& item:pending)if(item.output&&*item.output) {
   add(*item.output,item.info);auto e=item.source;e.api=Mapping;e.timestamp_ns=flash::now_ns();associate(e,*item.output);
   e.group_id=item.source.group_id;e.group_depth=item.source.group_depth;record(e,rc);
 }
 pending.clear();
}
void erase(ncclComm_t comm){auto& r=active_runtime();std::lock_guard<std::mutex> lock(r.mutex);r.comms.erase(reinterpret_cast<uintptr_t>(comm));}
template<class F> F original(const char* name,void* wrapper) {
 void* p=dlsym(RTLD_NEXT,name);
 if(!p)if(const char* path=getenv("FLASH_NCCL_LIBRARY")) {
   void* lib=dlopen(path,RTLD_NOW|RTLD_LOCAL|RTLD_NOLOAD);if(lib){p=dlsym(lib,name);dlclose(lib);}
 }
 if(!p||p==wrapper){fprintf(stderr,"FLASH_PROBE_RESOLVE_FATAL %s\n",name);_exit(127);}
 return reinterpret_cast<F>(p);
}
// PAPER: start/stop stream events, stop synchronize, elapsed milliseconds -> microseconds.
// ADAPTATION: fresh pair per timing scope (no cache), explicit unsupported/error records.
std::atomic<uint64_t> cuda_calls{0}, cuda_syncs{0};
void apply_boundary() {
 auto& r=active_runtime();uint64_t next=flash::boundary(r.handle);
 if(next!=UINT64_MAX)control=next;
 else {control=0;fprintf(stderr,"FLASH_CONTROL_BOUNDARY_ERROR\n");}
}
struct Cuda {
 decltype(&cudaGetDevice) device;
 decltype(&cudaStreamIsCapturing) capture;
 using Create = cudaError_t (*)(cudaEvent_t*);
 Create create;
 decltype(&cudaEventRecord) record;
 decltype(&cudaEventSynchronize) sync;
 decltype(&cudaEventElapsedTime) elapsed;
 decltype(&cudaEventDestroy) destroy;
 Cuda() {
 void* library=nullptr;
 if(const char* path=getenv("FLASH_CUDA_LIBRARY"))library=dlopen(path,RTLD_NOW|RTLD_NOLOAD|RTLD_LOCAL);
 #define LOAD(FIELD,NAME) FIELD=reinterpret_cast<decltype(FIELD)>(dlsym(RTLD_DEFAULT,#NAME));if(!FIELD&&library)FIELD=reinterpret_cast<decltype(FIELD)>(dlsym(library,#NAME))
 LOAD(device,cudaGetDevice);LOAD(capture,cudaStreamIsCapturing);LOAD(create,cudaEventCreate);
 LOAD(record,cudaEventRecord);LOAD(sync,cudaEventSynchronize);LOAD(elapsed,cudaEventElapsedTime);LOAD(destroy,cudaEventDestroy);
 #undef LOAD
 if(library)dlclose(library);
 }
 bool ready(){return device&&capture&&create&&record&&sync&&elapsed&&destroy;}
};
Cuda& cuda(){static Cuda c;return c;}
struct Timer {
 cudaEvent_t start=nullptr,stop=nullptr;cudaStream_t stream=nullptr;
 int device=-1;uint32_t status=0;int rc[11];double us=0;uint64_t block=0;
 Timer(){for(auto& v:rc)v=-1;}
 int call(cudaError_t value){++cuda_calls;return int(value);}
 void begin(flash::Event& e,cudaStream_t s) {
  stream=s;status=2;
  if(e.identity!=UNIQUE_ID_SHA256 || (!group_depth&&(e.api==Send||e.api==Recv)))return;
  auto& c=cuda();if(!c.ready())return;
  status=3;
  if((rc[0]=call(c.device(&device)))!=0)return;
  cudaStreamCaptureStatus capture{};
  if((rc[1]=call(c.capture(s,&capture)))!=0)return;
  if(capture!=cudaStreamCaptureStatusNone){status=2;return;}
  if((rc[2]=call(c.create(&start)))!=0)return;
  if((rc[3]=call(c.create(&stop)))!=0)return;
  if((rc[4]=call(c.record(start,s)))!=0)return;
  status=1;
 }
 void member(flash::Event& e,cudaStream_t s) {
  if(status!=1)return;
  int d=-1;auto& c=cuda();int result=call(c.device(&d));
  if(result!=0){rc[10]=result;status=3;}
  else if(s!=stream||d!=device||e.identity!=UNIQUE_ID_SHA256)status=2;
 }
 void finish(ncclResult_t result) {
  auto& c=cuda();
  if(result!=ncclSuccess)status=result==ncclInProgress?2:3;
  if(status==1) {
   if((rc[5]=call(c.record(stop,stream)))!=0)status=3;
   if(status==1) {
    uint64_t t=flash::now_ns();++cuda_syncs;rc[6]=call(c.sync(stop));block=flash::now_ns()-t;
    if(rc[6]!=0)status=3;
   }
   if(status==1){float ms=-1;rc[7]=call(c.elapsed(&ms,start,stop));
    if(rc[7]!=0||!std::isfinite(ms)||ms<0)status=3;else us=double(ms)*1000.0;}
  }
  // Destroy does not wait for unfinished work. All handles belong to the scope's device.
  // A multi-device Group is unsupported: restore only for resource destruction, then restore caller device.
  int current=device;bool changed=false;
  if((start||stop)&&c.device){int result=call(c.device(&current));
   if(result!=0){rc[10]=result;status=3;}
   else if(current!=device){
    auto set=reinterpret_cast<decltype(&cudaSetDevice)>(dlsym(RTLD_DEFAULT,"cudaSetDevice"));
    if(set){int result=call(set(device));changed=result==0;if(result){rc[10]=result;status=3;}}
    else {status=3;rc[10]=-2;}
   }
  }
  if(current==device||changed) {
   if(start){rc[8]=call(c.destroy(start));if(rc[8])status=3;start=nullptr;}
   if(stop){rc[9]=call(c.destroy(stop));if(rc[9])status=3;stop=nullptr;}
  }
  if(changed){auto set=reinterpret_cast<decltype(&cudaSetDevice)>(dlsym(RTLD_DEFAULT,"cudaSetDevice"));int result=call(set(current));if(result){rc[10]=result;status=3;}}
 }
 void fill(flash::Event& e,uint32_t scope){e.timing_scope=scope;e.timing_status=status;e.device=device;e.duration_us=us;e.sync_block_ns=block;memcpy(e.cuda_rc,rc,sizeof(rc));}
};
thread_local Timer group_timer;
thread_local bool group_timing_started=false;
thread_local std::vector<flash::Event> group_members;
void timing_prepare(flash::Event& e,cudaStream_t stream,Timer& timer) {
 if(!group_depth)apply_boundary();e.state=control&1;e.profile_epoch=control>>1;
 if(!e.state)return;
 if(group_depth) {
  if(!group_timing_started){group_timer=Timer();group_timer.begin(e,stream);group_timing_started=true;}
  else group_timer.member(e,stream);
 }else timer.begin(e,stream);
}
void timing_done(flash::Event e,cudaStream_t,Timer& timer,ncclResult_t result) {
 if(!e.state){record(e,result);return;}
 e.result=result;
 if(group_depth){
  if(result!=ncclSuccess)group_timer.status=result==ncclInProgress?2:3;
  group_members.push_back(e);
 }else {timer.finish(result);timer.fill(e,1);record(e,result);}
}
void timing_group_end(ncclResult_t result) {
 if(group_timing_started){
  group_timer.finish(result);
  for(auto e:group_members){group_timer.fill(e,2);record(e,static_cast<ncclResult_t>(e.result));}
 }
 group_members.clear();group_timing_started=false;
}
}
// Wrappers never hold metadata locks while invoking NCCL; return the exact NCCL rc.
// Metadata exceptions are confined to the monitoring path.
#define BEGIN(NAME,API,COMM) \
 static auto fn=original<decltype(&NAME)>(#NAME,reinterpret_cast<void*>(&NAME)); \
 Guard guard; if(!guard.outer)return fn
#define CALL_META(API,COMM) flash::Event e{};try{e=event(API,COMM);}catch(...){}
#define DONE(EXPR) auto rc=(EXPR);record(e,rc);return rc
#define COLLECTIVE(NAME,API,ARGS,PASS,META) \
extern "C" ncclResult_t NAME ARGS {BEGIN(NAME,API,comm) PASS; CALL_META(API,comm); \
 e.count=count;e.datatype=dtype;META;e.stream_ptr=reinterpret_cast<uintptr_t>(stream); \
 Timer timer;timing_prepare(e,stream,timer);auto rc=fn PASS;timing_done(e,stream,timer,rc);return rc;}
COLLECTIVE(ncclAllReduce,AllReduce,(const void* send,void* recv,size_t count,ncclDataType_t dtype,ncclRedOp_t op,ncclComm_t comm,cudaStream_t stream),(send,recv,count,dtype,op,comm,stream),e.op=op)
COLLECTIVE(ncclAllGather,AllGather,(const void* send,void* recv,size_t count,ncclDataType_t dtype,ncclComm_t comm,cudaStream_t stream),(send,recv,count,dtype,comm,stream),(void)0)
COLLECTIVE(ncclBroadcast,Broadcast,(const void* send,void* recv,size_t count,ncclDataType_t dtype,int root,ncclComm_t comm,cudaStream_t stream),(send,recv,count,dtype,root,comm,stream),e.peer=root)
COLLECTIVE(ncclBcast,Bcast,(void* buffer,size_t count,ncclDataType_t dtype,int root,ncclComm_t comm,cudaStream_t stream),(buffer,count,dtype,root,comm,stream),e.peer=root)
COLLECTIVE(ncclReduce,Reduce,(const void* send,void* recv,size_t count,ncclDataType_t dtype,ncclRedOp_t op,int root,ncclComm_t comm,cudaStream_t stream),(send,recv,count,dtype,op,root,comm,stream),e.op=op;e.peer=root)
COLLECTIVE(ncclReduceScatter,ReduceScatter,(const void* send,void* recv,size_t count,ncclDataType_t dtype,ncclRedOp_t op,ncclComm_t comm,cudaStream_t stream),(send,recv,count,dtype,op,comm,stream),e.op=op)
COLLECTIVE(ncclSend,Send,(const void* send,size_t count,ncclDataType_t dtype,int peer,ncclComm_t comm,cudaStream_t stream),(send,count,dtype,peer,comm,stream),e.peer=peer)
COLLECTIVE(ncclRecv,Recv,(void* recv,size_t count,ncclDataType_t dtype,int peer,ncclComm_t comm,cudaStream_t stream),(recv,count,dtype,peer,comm,stream),e.peer=peer)
extern "C" ncclResult_t ncclCommInitRank(ncclComm_t* output,int size,ncclUniqueId id,int rank) {
 BEGIN(ncclCommInitRank,InitRank,nullptr)(output,size,id,rank);CALL_META(InitRank,nullptr);
 Comm info;info.rank=rank;info.size=size;sha_id(id,info);e.comm_rank=rank;e.comm_size=size;memcpy(e.id_hash,info.hash,65);
 e.identity=group_depth?PENDING_GROUP:UNIQUE_ID_SHA256;
 auto rc=fn(output,size,id,rank);try{map_pending(output,info,e,rc);if(rc==ncclSuccess&&!group_depth&&output&&*output){
  associate(e,*output);
 }}catch(...){}if(rc==ncclInProgress){e.identity=UNSUPPORTED_INIT;memset(e.id_hash,0,65);}record(e,rc);return rc;
}
extern "C" ncclResult_t ncclCommInitRankConfig(ncclComm_t* output,int size,ncclUniqueId id,int rank,ncclConfig_t* config) {
 BEGIN(ncclCommInitRankConfig,InitConfig,nullptr)(output,size,id,rank,config);CALL_META(InitConfig,nullptr);
 Comm info;info.rank=rank;info.size=size;sha_id(id,info);e.comm_rank=rank;e.comm_size=size;memcpy(e.id_hash,info.hash,65);
 if(config&&config->blocking==0){info.identity=UNSUPPORTED_INIT;memset(info.hash,0,65);memset(e.id_hash,0,65);}
 e.identity=info.identity==UNSUPPORTED_INIT?UNSUPPORTED_INIT:(group_depth?PENDING_GROUP:UNIQUE_ID_SHA256);
 auto rc=fn(output,size,id,rank,config);try{map_pending(output,info,e,rc);if(rc==ncclSuccess&&!group_depth&&output&&*output){
  associate(e,*output);
 }}catch(...){}if(rc==ncclInProgress){e.identity=UNSUPPORTED_INIT;memset(e.id_hash,0,65);}record(e,rc);return rc;
}
extern "C" ncclResult_t ncclCommSplit(ncclComm_t comm,int color,int key,ncclComm_t* output,ncclConfig_t* config) {
 BEGIN(ncclCommSplit,Split,comm)(comm,color,key,output,config);CALL_META(Split,comm);
 e.peer=color;e.op=key;auto rc=fn(comm,color,key,output,config);
 try{Comm info;info.identity=UNRESOLVED_SPLIT;map_pending(output,info,e,rc);}catch(...){}record(e,rc);return rc;
}
extern "C" ncclResult_t ncclCommInitAll(ncclComm_t* comms,int size,const int* devices) {
 BEGIN(ncclCommInitAll,InitAll,nullptr)(comms,size,devices);CALL_META(InitAll,nullptr);e.identity=UNSUPPORTED_INIT;
 auto rc=fn(comms,size,devices);try{if(rc==ncclSuccess)for(int i=0;i<size;++i){Comm info;info.identity=UNSUPPORTED_INIT;info.rank=i;info.size=size;add(comms[i],info);}}catch(...){}
 record(e,rc);return rc;
}
extern "C" ncclResult_t ncclCommInitRankScalable(ncclComm_t* output,int size,int rank,int nId,ncclUniqueId* ids,ncclConfig_t* config) {
 BEGIN(ncclCommInitRankScalable,InitScalable,nullptr)(output,size,rank,nId,ids,config);CALL_META(InitScalable,nullptr);
 e.identity=UNSUPPORTED_INIT;auto rc=fn(output,size,rank,nId,ids,config);try{Comm info;info.identity=UNSUPPORTED_INIT;map_pending(output,info,e,rc);}catch(...){}record(e,rc);return rc;
}
extern "C" ncclResult_t ncclGroupStart() {
 BEGIN(ncclGroupStart,GroupStart,nullptr)();if(!group_depth)apply_boundary();CALL_META(GroupStart,nullptr);
 e.state=control&1;e.profile_epoch=control>>1;
 auto rc=fn();if(rc==ncclSuccess){if(!group_depth)group_id=++groups;++group_depth;e.group_id=group_id;e.group_depth=group_depth;}record(e,rc);return rc;
}
extern "C" ncclResult_t ncclGroupEnd() {
 BEGIN(ncclGroupEnd,GroupEnd,nullptr)();CALL_META(GroupEnd,nullptr);
 e.state=control&1;e.profile_epoch=control>>1;
 auto rc=fn();if(group_timing_started&&rc!=ncclSuccess)group_timer.status=rc==ncclInProgress?2:3;
 if(group_depth){--group_depth;if(!group_depth){timing_group_end(rc);try{finish_pending(rc);}catch(...){}group_id=0;}}
 record(e,rc);return rc;
}
#define COMM_OP(NAME,API,ERASE) \
extern "C" ncclResult_t NAME(ncclComm_t comm) { BEGIN(NAME,API,comm)(comm);CALL_META(API,comm); \
 auto rc=fn(comm);try{if(ERASE&&rc==ncclSuccess)erase(comm);}catch(...){}record(e,rc);return rc;}
COMM_OP(ncclCommFinalize,Finalize,false)
COMM_OP(ncclCommDestroy,Destroy,true)
COMM_OP(ncclCommAbort,Abort,true)
#define QUERY(NAME,API,TYPE) \
extern "C" ncclResult_t NAME(ncclComm_t comm,TYPE* value) {BEGIN(NAME,API,comm)(comm,value);CALL_META(API,comm);DONE(fn(comm,value));}
QUERY(ncclCommGetAsyncError,GetAsyncError,ncclResult_t)
QUERY(ncclCommCount,CommCount,int)
QUERY(ncclCommUserRank,CommUserRank,int)
extern "C" ncclResult_t ncclGetUniqueId(ncclUniqueId* id){BEGIN(ncclGetUniqueId,GetUniqueId,nullptr)(id);CALL_META(GetUniqueId,nullptr);DONE(fn(id));}
extern "C" ncclResult_t ncclGetVersion(int* v){BEGIN(ncclGetVersion,GetVersion,nullptr)(v);CALL_META(GetVersion,nullptr);DONE(fn(v));}
extern "C" ncclResult_t ncclCommRegister(ncclComm_t comm,void* buffer,size_t size,void** handle){BEGIN(ncclCommRegister,Register,comm)(comm,buffer,size,handle);CALL_META(Register,comm);e.count=size;DONE(fn(comm,buffer,size,handle));}
extern "C" ncclResult_t ncclCommDeregister(ncclComm_t comm,void* handle){BEGIN(ncclCommDeregister,Deregister,comm)(comm,handle);CALL_META(Deregister,comm);DONE(fn(comm,handle));}
extern "C" ncclResult_t ncclMemAlloc(void** p,size_t size){BEGIN(ncclMemAlloc,MemAlloc,nullptr)(p,size);CALL_META(MemAlloc,nullptr);e.count=size;DONE(fn(p,size));}
extern "C" ncclResult_t ncclMemFree(void* p){BEGIN(ncclMemFree,MemFree,nullptr)(p);CALL_META(MemFree,nullptr);DONE(fn(p));}

// ADAPTATION: local process manual control. Request is applied only at the next scope boundary.
extern "C" int flash_profile_request(uint32_t state,uint64_t epoch){return flash::request(active_runtime().handle,state,epoch);}
extern "C" uint64_t flash_profile_cuda_calls(){return cuda_calls.load();}
extern "C" uint64_t flash_profile_cuda_syncs(){return cuda_syncs.load();}
