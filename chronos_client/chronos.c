#include <time.h>
#include <stdlib.h>
#include <stdio.h>
#include <math.h>
#include <string.h>
#include <sys/time.h>
#include "chronos.h"
#include "tools.h"

#define MAX_LEN_IP 100

char** ips_pool;
double* times;


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
	for (int i = start; i < end; i++) {
		sum += times[i];
	}
	return sum / (end - start);
}

/**
 * Sends query to the given ip address.
 * @param ip - ip address to query
 * @param index - the index of the "times" array in which the offset will be stored
 * @return 1 on success, 0 on failure
 */
double send_query(char ip[], int index) {
	FILE *fp;
	char output[1035];
	char command[1000] = {0};

	// concatenate the ip to the "ntpdate" command
	snprintf(command, sizeof(command), "ntpdate -q %s", ip);

	// Open the command for reading.
	fp = popen(command, "r");
	if (fp == NULL) {
		return 0;
	}

	char server[MAX_LEN_IP] = {0};
	int result, stratum;
	double delay, offset;

	// Read the output a line at a time - output it.
	while (fgets(output, sizeof(output), fp) != NULL) {
		result = sscanf(output, "server %[:0-9.:], stratum %d, offset %lf, delay %lf", server, &stratum, &offset, &delay);
		if (result == 4) { // the line matched the required format
			if (stratum == 0 && offset == 0 && delay == 0) {
				// error connecting to this server - then exit
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

/**
 * Loads the pool of ips (that was generated during the "calibration" stage)
 * @param filename - path to the file contains the ips pool
 * @param n - number of ips in the pool
 */
void load_pool(char* filename, int* n) {
	FILE* fp;
	char* line = NULL;
	size_t len = 0;
	int counter = 0;

	// count the lines in the file
	fp = fopen(filename, "r");
	if (fp == NULL) {
		free_ips_pool(counter, ips_pool);
		return;
	}
	while ((getline(&line, &len, fp)) != -1)
		counter++;
	fclose(fp);

	// update the pool_size
	*n = counter;

	allocate_ips_pool(counter, &ips_pool);
	// read the ips into "ips_pool"
	fp = fopen(filename, "r");
	for (int i = 0; i < counter; i++) {
		getline(&line, &len, fp);
		strtok(line, "\n");
		strcpy(ips_pool[i], line);
	}
	fclose(fp);
}

/**
 * Samples m random servers from the servers pool and gets their offsets.
 * @param m - number of servers to be sampled
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
		while (!send_query(ips_pool[random_index], counter) && chosen_counter < pool_size) {
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
 * Applies the Chronos algorithm
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
		free_ips_pool(pool_size, ips_pool);
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

/**
 * Reads the configuration file and loads its content into the variables
 * @return 1 on success, 0 on failure
 */
int read_config(int* m, double* d, double* w, double* drift, int* k,
				int* d_chronos, double* truth) {
	FILE* config_file;
	FILE* truth_file;
	char* line = NULL;
	size_t len = 0;

	config_file = fopen("./chronos_config.txt", "r");
	if (config_file == NULL)
		return 0;

	getline(&line, &len, config_file);

	sscanf(line, "%d %lf %d %lf %lf %d", m, d, k, w, drift, d_chronos);
	fclose(config_file);

	truth_file = fopen("./chronos_truth.txt", "r");
	if (truth_file == NULL)
		return 0;

	getline(&line, &len, truth_file);

	sscanf(line, "%lf", truth);
	fclose(truth_file);
	return 1;
}

/**
 * Reads the parameters and runs the Chronos algorithm
 * @return Chronos offset
 */
double chronos_main() {
	int m, k, d_chronos, pool_size;
	double d, w, drift, truth;
	if (!read_config(&m, &d, &w, &drift, &k, &d_chronos, &truth))
		exit(EXIT_FAILURE);
	load_pool("./chronos_test_pool.txt", &pool_size);
	double offset = chronos(m, d, w, (drift * d_chronos) / 1000, k, truth, pool_size);
	free_ips_pool(pool_size, ips_pool);
	free(times);

	FILE *out = fopen("./chronos_truth.txt", "w");
	fprintf(out, "%f", offset);
	fclose(out);

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
