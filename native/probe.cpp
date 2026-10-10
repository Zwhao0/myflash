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
 e.count=count;e.datatype=dtype;META;e.stream_ptr=reinterpret_cast<uintptr_t>(stream);DONE(fn PASS);}
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
 BEGIN(ncclGroupStart,GroupStart,nullptr)();CALL_META(GroupStart,nullptr);
 auto rc=fn();if(rc==ncclSuccess){if(!group_depth)group_id=++groups;++group_depth;e.group_id=group_id;e.group_depth=group_depth;}record(e,rc);return rc;
}
extern "C" ncclResult_t ncclGroupEnd() {
 BEGIN(ncclGroupEnd,GroupEnd,nullptr)();CALL_META(GroupEnd,nullptr);
 auto rc=fn();if(group_depth){--group_depth;if(!group_depth){try{finish_pending(rc);}catch(...){}group_id=0;}}
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
