#include <stdio.h>
#include <string.h>
#include <sys/time.h>
#include <stdlib.h>
#include "tools.h"

char** ips_pool;

/**
 * This function finds pool_size servers and puts their ips in the ips_pool.
 * @param pool_size - number of servers needed to be in the pool
 * @param max_time_secs - time limit for extracting server to the pool
 */
void calibration(int pool_size, int max_time_secs, char** zone_urls) {
    allocate_ips_pool(pool_size, &ips_pool);

    struct timeval start;
    gettimeofday(&start, NULL);
    get_ip(0, 0, pool_size, max_time_secs, start, ips_pool, zone_urls);
}


/**
 * This function reads the urls of the given zone and creates an array that contains them.
 * @param filename - file containing the urls of the current zone
 */
char** read_zones(char* filename) {
    char base_add[100] = "./zones_urls/";
    strcat(base_add, filename);
    strcat(base_add, ".txt");

    FILE* fp;
    fp = fopen(base_add, "r");
    if (fp == NULL) {
        return NULL;
    }
    // memory allocation (and free if needed)
    char** zones = malloc(NUM_URLS * sizeof(zones));
    if (zones == NULL)
        return NULL;
    for (int i = 0; i < NUM_URLS; i++) {
        zones[i] = malloc(MAX_LEN_IP * sizeof(char*));
        if (zones[i] == NULL) {
            for (int j = 0; j < i; j++)
                free(zones[j]);
            free(zones);
            return NULL;
        }
    }

    char* line = NULL;
    size_t len = 0;
    int counter = 0;
    while ((getline(&line, &len, fp)) != -1) {
        strtok(line, "\n");
        strcpy(zones[counter], line);
        counter++;
    }
    return zones;
}

int main(int argc, char* argv[]) {
    // [zone] [pool_size] [time_limit]
    printf("STARTING\n");
    int pool_size = (int) strtod(argv[2], NULL);
    int time_limit = (argc > 3) ? (int) strtod(argv[3], NULL) : 99999999;
    char** z = read_zones(argv[1]);
    calibration(pool_size, time_limit, z);
    write_result("./ips_pool_usa.txt", ips_pool, pool_size);  //TODO: CHANGE FILENAME
    free_memory(0, 0, pool_size, ips_pool, NULL);
}
