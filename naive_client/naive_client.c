#include <stdio.h>
#include <stdlib.h>
#include <sys/time.h>
#include <math.h>
#include <time.h>
#include <string.h>
#include <unistd.h>
#include "logger.h"

char log_file[100] = "./watchdog_logger";

/**
 * Calculates the difference between the two given times in seconds.
 */
double time_diff(struct timeval tv1, struct timeval tv2) {
	return fabs((double) (tv2.tv_usec - tv1.tv_usec) / 1000000 + (double) (tv2.tv_sec - tv1.tv_sec));
}

/**
 * runs the "ntpq -p" command and parse its output to get the offset of the peer that
 * the process sync with (the selected peer is the one that begins with "*")
 * @return the peer's offset
 */
double getNTPv4Offset() {
	FILE *fp;
	char remote[100] = {0};
	char refid[100] = {0};
	char t;
	int st, when, poll, reach;
	double delay, offset, jitter;
	char s0[100], s1[100], s2[100], s3[100], s4[100], s5[100], s6[100], s7[100], s8[100] = {0};
	char output[1035];

	// Open the command for reading.
	fp = popen("ntpq -p", "r");
	if (fp == NULL) {
		logger("error running the 'ntpq -p' command", log_file);
		return 0;
	}
	if (fgets(output, sizeof(output), fp) != NULL) {
		fgets(output, sizeof(output), fp);
		while (fgets(output, sizeof(output), fp) != NULL) {
			if (output[0] != '*')
				continue;
			sscanf(output, "%s%[: .:]%s%[: .:]%d%[: .:]%s%[: .:]%d%[: .:]%d%[: .:]%d%[: .:]%lf%[: .:]%lf%[: .:]%lf",
				   remote, s0, refid, s1, &st, s2, &t, s3, &when, s4, &poll, s5, &reach, s6, &delay, s7,
				   &offset, s8, &jitter);
			pclose(fp);

			offset = offset / 1000; // convert from milliseconds to seconds

			char log_msg[1000] = {0};
			snprintf(log_msg, sizeof(log_msg), "finished naive iteration. offset = %f", offset);
			logger(log_msg, log_file);
			printf("naive offset = %f\n", offset);

			return offset;
		}
	}
	pclose(fp);
	logger("naive client doesn't have peer to sync with", log_file);
	return 0;
}

/**
 * Reads the configuration file and insert the value into variable
 * @return 1 on success, 0 on failure
 */
int read_config_naive(int* deltaNTP) {
	FILE *fp;
	char *line = NULL;
	size_t len = 0;

	fp = fopen("./naive_config.txt", "r");
	if (fp == NULL)
		return 0;

	getline(&line, &len, fp);

	sscanf(line, "%d", deltaNTP);
	fclose(fp);
	return 1;
}

/**
 * Updates the local clock using the "timedatectl set-time" command
 */
void clock_update(double offset) {
	if (fabs(offset) < 0.1) {
		return;
	}
	char command[100] = {0};
	if (offset >= 0) {
		sprintf(command, "sudo timedatectl set-time '+%f'\n", offset);
	} else {
		sprintf(command, "sudo timedatectl set-time '%f ago'\n", -offset);
	}
	FILE *fp;
	fp = popen(command, "r");
	pclose(fp);
}

/**
 * Runs the NTP process:
 * takes the offset of NTPv4 every "deltaNTP" minutes, and updates the clock accordingly
 */
void naive_process(int deltaNTP, int totalTime) {
	logger("starting watchdog process", log_file);
	struct timeval starting_time;
	struct timeval cur_time;
	struct timeval iteration_starting_time;

	gettimeofday(&starting_time, NULL);
	gettimeofday(&cur_time, NULL);

	double naiveOffset = 0;
	while (time_diff(starting_time, cur_time) < (totalTime * 60)) {
		gettimeofday(&iteration_starting_time, NULL);
		naiveOffset = getNTPv4Offset();
//        clock_update(naiveOffset);
		gettimeofday(&cur_time, NULL);
		double time_taken = time_diff(iteration_starting_time, cur_time);
		int to_sleep = (int) (deltaNTP * 60 - time_taken);
		if (to_sleep > 0)
			sleep(to_sleep);
		gettimeofday(&cur_time, NULL);
	}
}

int main(int argc, char* argv[]) {
	//  config_file: [deltaNTP]
	//  input parameter: total_time (minutes)

//    popen("sudo timedatectl set-ntp 0", "r");

	// create a log file
	time_t now;
	time(&now);
	strcat(log_file, ctime(&now));
	strcat(log_file, ".log");

	int deltaNTP;
	if (!read_config_naive(&deltaNTP)) {
		logger("config file error", log_file);
		exit(EXIT_FAILURE);
	}

	char* ptr;
	int totalTime = (int) strtol(argv[1], &ptr, 10); // in minutes

	naive_process(deltaNTP, totalTime);
//    popen("timedatectl set-ntp 1", "r");
}
