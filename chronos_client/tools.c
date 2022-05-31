#include <netdb.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <sys/time.h>
#include <math.h>
#include "tools.h"


/**
 * Calculates the difference between the two given times in seconds.
 */
double time_diff(struct timeval tv1, struct timeval tv2) {
    return fabs((double) (tv2.tv_usec - tv1.tv_usec) / 1000000 + (double) (tv2.tv_sec - tv1.tv_sec));
}

void allocate_ips_pool(int n, char*** ips_pool) {
    *ips_pool = (char**)malloc(n * sizeof(char*));
    if (*ips_pool == NULL) {
        printf("memory allocation failed.\n");
        exit(EXIT_FAILURE);
    }
    for (int i = 0; i < n; i++) {
        (*ips_pool)[i] = (char*)malloc(MAX_LEN_IP * sizeof(char));
        if ((*ips_pool)[i] == NULL) {
            printf("memory allocation failed.\n");
            for (int j = 0; j < i; j++) {
                free((*ips_pool)[j]);
                (*ips_pool)[j] = NULL;
            }
            free(*ips_pool);
            *ips_pool = NULL;
            exit(EXIT_FAILURE);
        }
    }
}

void get_ip(int ips_found, int to_replace, int rest_to_find, int max_time, struct timeval start,
        char** ips_pool, char** zone_urls) {
    int is_unique;
    char* cur_ip;
    struct hostent *hp;
    struct in_addr ip_addr;
    struct timeval cur_time;

    gettimeofday(&cur_time, NULL);
    while ((time_diff(start, cur_time) < max_time) && (rest_to_find > 0)) {
        for (int i = 0; i < NUM_URLS; i++) {
            is_unique = 1;

            // get the ip of the current url:
            hp = gethostbyname(zone_urls[i]);
            if (!hp)
                continue;
            ip_addr = *(struct in_addr *) (hp->h_addr);
            cur_ip = inet_ntoa(ip_addr);

            // check if it is already exist:
            for (int j = 0; j < ips_found; j++) {
                if (strcmp(cur_ip, ips_pool[j]) == 0) {
                    is_unique = 0;
                    break;
                }
            }
            // if it is not exist yet - add it to the ips_pool list
            if (is_unique) {
                printf("new ip: %s, number: %d\n", cur_ip, ips_found);
                strcpy(ips_pool[to_replace], cur_ip);
                if (--rest_to_find == 0)
                    return;
                to_replace++;
                ips_found++;
            }
        }
        gettimeofday(&cur_time, NULL);
        sleep(5);
    }
}

/**
 * Frees dynamic allocated memory
 */
void free_memory(int m, int free_times, int pool_size, char** ips_pool, double* times) {
    for (int i = 0; i < pool_size; i++) {
        free(ips_pool[i]);
        ips_pool[i] = NULL; // todo: check NULL
    }
    free(ips_pool);
    ips_pool = NULL;
    if (free_times) {
        free(times);
    }
}

void write_result(char* filename, char** result, int len_result) {
    FILE *out=fopen(filename,"w");
    for (int i = 0; i < len_result; i++) {
        fputs(result[i], out);
        fputs("\n", out);
    }
    fclose(out);
}