/* ADAPTATION: standalone layout probe, compiled against fixed release headers.
 * No production state or function pointer is modified. */
#include <stdio.h>
#include <stddef.h>
#include "abc_rand_pcg_local.h"
int main(void) {
    printf("{\"sizeof\":%zu,\"alignof\":%zu,\"u64_sizeof\":%zu,"
           "\"state\":%zu,\"increment\":%zu,\"state512\":%zu,"
           "\"increment512\":%zu,\"MULTIPLIER_8steps\":%zu,"
           "\"INCREMENT_8steps\":%zu}\n",
           sizeof(local_pcg32_random_t), _Alignof(local_pcg32_random_t), sizeof(U64),
           offsetof(local_pcg32_random_t, state),
           offsetof(local_pcg32_random_t, increment),
           offsetof(local_pcg32_random_t, state512),
           offsetof(local_pcg32_random_t, increment512),
           offsetof(local_pcg32_random_t, MULTIPLIER_8steps),
           offsetof(local_pcg32_random_t, INCREMENT_8steps));
    return 0;
}
