// Synthetic CUDA fault fixture only, no GPU experiment.
#include <cuda_runtime_api.h>
#include <cstdint>
static int mode=0,created=0,destroyed=0,waited=0;
extern "C" void flash_mock_cuda_mode(int value){mode=value;}
extern "C" int flash_mock_cuda_live(){return created-destroyed;}
extern "C" int flash_mock_cuda_waits(){return waited;}
extern "C" cudaError_t cudaGetDevice(int* d){*d=0;return mode==1?cudaErrorInvalidValue:cudaSuccess;}
extern "C" cudaError_t cudaStreamIsCapturing(cudaStream_t,cudaStreamCaptureStatus* s){*s=mode==2?cudaStreamCaptureStatusActive:cudaStreamCaptureStatusNone;return cudaSuccess;}
extern "C" cudaError_t cudaEventCreate(cudaEvent_t* e){if(mode==3)return cudaErrorMemoryAllocation;*e=reinterpret_cast<cudaEvent_t>(new int(++created));return cudaSuccess;}
extern "C" cudaError_t cudaEventRecord(cudaEvent_t,cudaStream_t){return mode==4?cudaErrorInvalidResourceHandle:cudaSuccess;}
extern "C" cudaError_t cudaEventSynchronize(cudaEvent_t){++waited;return mode==5?cudaErrorLaunchFailure:cudaSuccess;}
extern "C" cudaError_t cudaEventElapsedTime(float* ms,cudaEvent_t,cudaEvent_t){*ms=mode==7?-1.0f:2.5f;return mode==6?cudaErrorInvalidResourceHandle:cudaSuccess;}
extern "C" cudaError_t cudaEventDestroy(cudaEvent_t e){delete reinterpret_cast<int*>(e);++destroyed;return cudaSuccess;}
