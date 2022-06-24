#include <time.h>
#include <stdlib.h>
#include <stdio.h>
#include <math.h>
#include <string.h>
#include <sys/time.h>
#include "chronos.h"
#include "tools.h"

#define MAX_LEN_IP 100  //todo: ?

//int pool_size;// = 50; // todo: get it as a parameter
char** ips_pool;
//c_time** times;
double* times;

//c_time* allocate_ctime(double offset, int stratum) {
//    c_time* time = malloc(sizeof(c_time));
//    if (time == NULL) return NULL;
//    time->offset = offset;
//    time->stratum = stratum;
//    return time;
//}

/**
 * Compares between 2 elements (used in the qsort function).
 * @return if the first element is grater than the second - returns positive number,
 *         if the second element is smaller than the second - returns negative number,
 *         if the two elements are equal - returns 0
 */
int comp(const void * elem1, const void * elem2) {
	double t1 = *(double *) elem1;
	double t2 = *(double *) elem2;
	return (int) ((t1 - t2)*10000);
}

/**
 * Calculates the average of the offsets array.
 * @param offsets_arr - array of the offsets from the 'sample' level
 * @param start - index to start calculating the average from
 * @param end - index to finish calculating the average from
 * @return the average
 */
double calculate_average(int start, int end) {
	double sum = 0;
//    printf("after bi-sided-trim:\n");
	for (int i = start; i < end; i++) {
		sum += times[i];
//        printf("%lf\n", times[i]);
	}
//    printf("--------------------\n");
	return sum / (end - start);
}

/**
 * Sends query to the given ip address.
 * @param ip - ip address to query
 * @param offset - variable to hold the offset we got from the query
 * @return 1 on success, 0 on failure
 */
double send_query(char ip[], int index) {
        printf("send query to ip: %s\n", ip);
	FILE *fp;
	char output[1035];
	char command[1000] = {0};
	snprintf(command, sizeof(command), "ntpdate -q %s", ip);
	printf("%s\n", command);
	// Open the command for reading.
	fp = popen(command, "r");  //todo: disable print if ip is not valid
	if (fp == NULL) {
		return 0;
	}
	char server[100] = {0};
	int result, stratum;
	double delay, offset;
	// Read the output a line at a time - output it.
	while (fgets(output, sizeof(output), fp) != NULL) {
		result = sscanf(output, "server %[:0-9.:], stratum %d, offset %lf, delay %lf", server, &stratum, &offset, &delay);
		if (result == 4) {
			if (stratum == 0 && offset == 0 && delay == 0) {
				pclose(fp);
				return 0;
			}
			times[index] = offset;
			pclose(fp);
			return 1;
		}
	}
	// close
	pclose(fp);
	return 0;
}

void load_pool(char* filename, int n) {
	allocate_ips_pool(n, &ips_pool);
	FILE* fp;
	fp = fopen(filename, "r");
	if (fp == NULL) {
		free_memory(0, 0, n, ips_pool, times);
		return;
	}

	char* line = NULL;
	size_t len = 0;
	int counter = 0;
	while ((getline(&line, &len, fp)) != -1) {
		strtok(line, "\n");
		strcpy(ips_pool[counter], line);
		counter++;
	}
    printf("count = %d\n", counter);
    for (int i = 0; i < n; i++) printf("%s\n", ips_pool[i]);
}

/**
 * This function samples m servers from the servers_pool and gets their offsets.
 * @param m - number of servers to be sampled
 * @return
 */
void sample(int m, int pool_size) {
	int chosen[pool_size];
	memset(chosen, 0, pool_size * sizeof(int));
	int counter = 0;
	int chosen_counter = 0;
	int random_index;
	struct timeval start;

	srand(time(NULL));
	// get m random indexes
	while (counter < m && chosen_counter < pool_size) {
		random_index = rand() % pool_size;
		if (chosen[random_index])
			continue;
		while (!send_query(ips_pool[random_index], counter) && chosen_counter < pool_size) { // todo: check if needed
			// try another index
			chosen[random_index] = 1;
			random_index = rand() % pool_size;
			while (chosen[random_index]) {
				random_index = rand() % pool_size;
			}
			chosen_counter++;
		}
		chosen_counter++;
		counter++;
		chosen[random_index] = 1;
	}
}

/**
 * Apply the Chronos algorithm
 * @param m - number of servers chosen at random from the server pool
 * @param d - number of outliers removed from each end of the ordered m samples
 * @param w - an upper bound on the distance from the UTC of the local time
 *            at any NTP server with an accurate clock (“truechimer”)
 * @param err - constant parameter for the error
 * @param k - panic trigger
 * @param truth - the offset from the last synchronization
 * @return Updated offset
 */
double chronos(int m, double d, double w, double err, int k, double truth, int pool_size) {
	int counter  = 0;
	double max;
	double min;
	double avg;
	times = malloc(m * sizeof(double));
	if (times == NULL) {
		free_memory(0, 0, pool_size, ips_pool, times);
		exit(EXIT_FAILURE);
	}
	int partition = (int) (d * m);
	while (counter < k) {
		sample(m, pool_size);
		qsort(times, m, sizeof(double), comp);
		max = times[m - partition - 1];
		min = times[partition];
		avg = calculate_average(partition, m - partition);
		if ((fabs(max - min) <= 2 * w) && (fabs(avg - truth) < err + 2 * w))
			return avg;
		counter++;
	}
	printf("PANIC\n");
	// panic mode:
	times = realloc(times, pool_size * sizeof(double));
	sample(pool_size, pool_size);
	qsort(times, pool_size, sizeof(double), comp);
	return calculate_average(pool_size/3, (2 * pool_size) / 3);
}

int read_config(int* m, double* d, double* w, double* drift, int* k,
				int* d_chronos, int* pool_size, double* truth) {
	FILE* fp;
	FILE* fp2;
	char* line = NULL;
	size_t len = 0;

	fp = fopen("./chronos_config.txt", "r");
	if (fp == NULL)
		return 0;

	getline(&line, &len, fp);

	sscanf(line, "%d %lf %d %lf %lf %d %d", m, d, k, w, drift, d_chronos, pool_size);
	fclose(fp);

	fp2 = fopen("./chronos_truth.txt", "r");
	if (fp2 == NULL)
		return 0;

	getline(&line, &len, fp2);

	sscanf(line, "%lf", truth);
	fclose(fp2);
	return 1;
}

double chronos_main() {
	int m, k, d_chronos, pool_size;
	double d, w, drift, truth;
	if (!read_config(&m, &d, &w, &drift, &k, &d_chronos, &pool_size, &truth))
		exit(EXIT_FAILURE);
	load_pool("./chronos_test_pool.txt", pool_size);
	printf("pool size = %d\n", pool_size);
	double offset = chronos(m, d, w, (drift * d_chronos) / 1000, k, truth, pool_size);
	free_memory(m, 1, pool_size, ips_pool, times);
//    printf("chronos offset:\n%lf\n" , offset);
	return offset;
}

//int main(int argc, char* argv[]) {
//	double offset = chronos_main();
//
//	char offset_str[50];
//	snprintf(offset_str, 50, "%f", offset);
//
//	FILE *out = fopen("./chronos_truth.txt", "w");
//	fputs(offset_str, out);
//	fclose(out);
//
//	printf("offset = %lf\n", offset);
//	return 0;
//}
