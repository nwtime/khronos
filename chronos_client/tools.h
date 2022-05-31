#ifndef CHRONOS_C_TOOLS_H
#define CHRONOS_C_TOOLS_H

#define MAX_LEN_IP 100
#define NUM_URLS 4

double time_diff(struct timeval tv1, struct timeval tv2);

void allocate_ips_pool(int n, char*** ips_pool);

void get_ip(int ips_found, int to_replace, int rest_to_find, int max_time,
            struct timeval start, char** ips_pool, char** zone_urls);

/**
 * Frees dynamic allocated memory
 */
void free_memory(int m, int free_times, int pool_size, char** ips_pool, double* times);

void write_result(char* filename, char** result, int len_result);
#endif //CHRONOS_C_TOOLS_H
