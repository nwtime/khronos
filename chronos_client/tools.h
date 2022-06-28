#ifndef CHRONOS_C_TOOLS_H
#define CHRONOS_C_TOOLS_H

#define MAX_LEN_IP 100
#define NUM_URLS 4

double time_diff(struct timeval tv1, struct timeval tv2);

void allocate_ips_pool(int n, char*** ips_pool);

void free_ips_pool(int pool_size, char** ips_pool);

#endif //CHRONOS_C_TOOLS_H
