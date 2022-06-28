#include <stdio.h>
#include <string.h>
#include <sys/time.h>
#include <stdlib.h>
#include <netdb.h>
#include <unistd.h>
#include <arpa/inet.h>
#include "tools.h"

#define SLEEP_PERIOD 5

char** ips_pool;


/**
 * Finds "pool_size" servers and inserts their ips into the ips_pool.
 * @param pool_size - number of servers needed to be in the pool
 * @param max_time - time limit for extracting server to the pool (in minutes)
 * @return number of ips that were found
 */
int calibration(int pool_size, int max_time, char** zone_urls) {
	allocate_ips_pool(pool_size, &ips_pool);
	int is_unique;
	int ips_found = 0;
	char* cur_ip;
	struct hostent *hp;
	struct in_addr ip_addr;

	struct timeval start;
	struct timeval cur_time;
	gettimeofday(&start, NULL);
	gettimeofday(&cur_time, NULL);

	while ((time_diff(start, cur_time) < max_time*60)) {
		for (int i = 0; i < NUM_URLS; i++) {
			is_unique = 1;
			// get an ip from the current url:
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
				strcpy(ips_pool[ips_found], cur_ip);
				if (++ips_found == pool_size)
					return pool_size;
			}
		}
		gettimeofday(&cur_time, NULL);
		sleep(SLEEP_PERIOD);
	}
	return ips_found;
}


/**
 * Reads the urls of the given zone and creates an array that contains them.
 * @param filename - file containing the urls of the current zone
 */
char** read_zones(char* filename) {
	// "create" the path to the file
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

	// read the lines of the file into 'zones'
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

/**
 * Writes the result into file
 */
void write_result(char* filename, char** result, int len_result) {
	FILE *out=fopen(filename,"w");
	for (int i = 0; i < len_result; i++) {
		fputs(result[i], out);
		fputs("\n", out);
	}
	fclose(out);
}


int main(int argc, char* argv[]) {
	// input parameters: [zone (string)] [pool_size (int)] [time_limit - minutes (int)]
	int pool_size = (int) strtod(argv[2], NULL);
	int time_limit = (argc > 3) ? (int) strtod(argv[3], NULL) : 99999999;
	char** zones = read_zones(argv[1]);
	if (zones == NULL) {
		printf("Error reading zones file\n");
		exit(EXIT_FAILURE);
	}

	int num_ips = calibration(pool_size, time_limit, zones);

	char filename[100] = "./ips_pool_";
	strcat(filename, argv[1]);
	strcat(filename, ".txt");
	write_result(filename, ips_pool, num_ips);

	free_ips_pool(pool_size, ips_pool);
}
