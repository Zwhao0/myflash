// Synthetic CPU fixture only. This is not NCCL/GPU correctness evidence.
#include <nccl.h>
#include <cstdint>
thread_local int mock_depth=0;
extern "C" ncclResult_t ncclGetVersion(int* p){*p=22703;return ncclSuccess;}
extern "C" ncclResult_t ncclCommInitRank(ncclComm_t* p,int size,ncclUniqueId id,int rank){*p=reinterpret_cast<ncclComm_t>(new int(rank));return ncclSuccess;}
extern "C" ncclResult_t ncclCommInitRankConfig(ncclComm_t* p,int size,ncclUniqueId id,int rank,ncclConfig_t* config){if(config&&config->blocking==0)return ncclInProgress;return ncclCommInitRank(p,size,id,rank);}
extern "C" ncclResult_t ncclAllReduce(const void* s,void* r,size_t n,ncclDataType_t dtype,ncclRedOp_t op,ncclComm_t comm,cudaStream_t stream) {
 if(n==42)return ncclInvalidArgument;
 if(n>32)return ncclInvalidUsage;
 for(size_t i=0;i<n;++i)static_cast<int64_t*>(r)[i]=2*static_cast<const int64_t*>(s)[i];
 return ncclSuccess;
}
extern "C" ncclResult_t ncclGroupStart(){++mock_depth;return ncclSuccess;}
extern "C" ncclResult_t ncclGroupEnd(){if(!mock_depth)return ncclInvalidUsage;--mock_depth;return ncclSuccess;}
extern "C" ncclResult_t ncclCommDestroy(ncclComm_t p){delete reinterpret_cast<int*>(p);return ncclSuccess;}
extern "C" ncclResult_t flash_mock_nonblocking() {
 ncclConfig_t config=NCCL_CONFIG_INITIALIZER;config.blocking=0;ncclComm_t comm=nullptr;ncclUniqueId id{};return ncclCommInitRankConfig(&comm,2,id,0,&config);
}
