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

double getIPv4Offset() {
    FILE *fp;
    char remote[100] = {0};
    char refid[100] = {0};
    char t;
    int st, when, poll, reach;
    double delay, offset, jitter;
    char bla[100] = {0};
    char bla1[100] = {0};
    char bla2[100] = {0};
    char bla3[100] = {0};
    char bla4[100] = {0};
    char bla5[100] = {0};
    char bla6[100] = {0};
    char bla7[100] = {0};
    char bla8[100] = {0};
    char output[1035];
    // Open the command for reading.
    fp = popen("ntpq -p", "r");  //todo: disable print if ip is not valid
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
                   remote, bla, refid, bla1, &st, bla2, &t, bla3, &when, bla4, &poll, bla5, &reach, bla6, &delay, bla7,
                   &offset, bla8, &jitter);
            pclose(fp);
            offset = offset / 1000;
            char log_msg[1000] = {0};
            snprintf(log_msg, sizeof(log_msg), "finished naive iteration. offset = %f, remote ip = %s, refid = %s", offset, remote, refid);
            logger(log_msg, log_file);
            printf("naive offset = %f\n", offset);
            return offset;
        }
    }
    pclose(fp);
    logger("naive client doesn't have peer to sync with", log_file);
    return 0;
}

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

void clock_update(double offset) {
    char command[100] = {0};
//    if (fabs(offset) < 0.1) {
//        return;
//    }
    if (offset >= 0) {
        sprintf(command, "timedatectl set-time '+%f'\n", offset);
    } else {
        sprintf(command, "timedatectl set-time '%f ago'\n", -offset);
    }
    popen(command, "r");
}

int main(int argc, char* argv[]) {
    // config_file: [deltaNTP]
    popen("timedatectl set-ntp 0", "r");
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
    struct timeval starting_time;
    struct timeval cur_time;
    struct timeval iteration_starting_time;

    gettimeofday(&starting_time, NULL);
    gettimeofday(&cur_time, NULL);

    double naiveOffset = 0;
    logger("strating watchdog process", log_file);
    while (time_diff(starting_time, cur_time) < (totalTime * 60)) {
        gettimeofday(&iteration_starting_time, NULL);
        naiveOffset = getIPv4Offset();
        clock_update(naiveOffset);
        gettimeofday(&cur_time, NULL);
        double time_taken = time_diff(iteration_starting_time, cur_time);
        int to_sleep = (int) (deltaNTP * 60 - time_taken);
        if (to_sleep > 0)
            sleep(to_sleep);
        gettimeofday(&cur_time, NULL);
    }
    popen("timedatectl set-ntp 1", "r");
    return 0;
}
