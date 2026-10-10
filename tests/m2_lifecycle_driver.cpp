// UPSTREAM: NCCL 2.27.3 public config initializer; no CUDA kernels.
#include <nccl.h>
#include <cstring>
extern "C" ncclResult_t flash_m2_init_config(ncclComm_t* comm,int size,const void* bytes,int rank) {
 ncclUniqueId id;memcpy(id.internal,bytes,sizeof(id.internal));
 ncclConfig_t config=NCCL_CONFIG_INITIALIZER;config.blocking=1;
 return ncclCommInitRankConfig(comm,size,id,rank,&config);
}
extern "C" ncclResult_t flash_m2_init_rank(ncclComm_t* comm,int size,const void* bytes,int rank) {
 ncclUniqueId id;memcpy(id.internal,bytes,sizeof(id.internal));return ncclCommInitRank(comm,size,id,rank);
}
