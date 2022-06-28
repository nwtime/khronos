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

/**
 * Allocates memory for ips pool (array of strings)
 * @param n - number of ips in the pool
 * @param ips_pool - pointer to the pool
 */
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

/**
 * Frees dynamic allocated memory
 */
void free_ips_pool(int pool_size, char** ips_pool) {
	for (int i = 0; i < pool_size; i++) {
		free(ips_pool[i]);
		ips_pool[i] = NULL;
	}
	free(ips_pool);
	ips_pool = NULL;
}

