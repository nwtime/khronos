#ifndef CHRONOS_C_CHRONOS_H
#define CHRONOS_C_CHRONOS_H

#include <time.h>
#include <stdlib.h>
#include <stdio.h>
#include <math.h>
#include <netdb.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <string.h>
#include <time.h>
#include <sys/time.h>

typedef struct {
    double offset;
    int stratum;
} c_time;

int comp(const void * elem1, const void * elem2);

double calculate_average(int start, int end);

//double time_diff(struct timeval tv1, struct timeval tv2);

double send_query(char ip[], int index);

void calibration(int n, int max_time_secs);

void sample(int m, int pool_size);

//void free_memory(int m, int free_times);

double chronos(int m, double d, double w, double err, int k, double truth, int pool_size);

double chronos_main();

//float foo();

//const char* zone_urls[] =
//// "global":
////        {"0.pool.ntp.org",
////         "1.pool.ntp.org",
////         "2.pool.ntp.org",
////         "3.pool.ntp.org"};
//
//// "europe":
//        {"0.europe.pool.ntp.org",
//         "1.europe.pool.ntp.org",
//         "2.europe.pool.ntp.org",
//         "3.europe.pool.ntp.org"};
//
//// "uk":
////        {"0.uk.pool.ntp.org",
////         "1.uk.pool.ntp.org",
////         "2.uk.pool.ntp.org",
////         "3.uk.pool.ntp.org"};
//
////"usa":
////        {"0.us.pool.ntp.org",
////        "1.us.pool.ntp.org",
////        "2.us.pool.ntp.org",
////        "3.us.pool.ntp.org"};
//
////"canada":
////        {"0.ca.pool.ntp.org",
////        "1.ca.pool.ntp.org",
////        "2.ca.pool.ntp.org",
////        "3.ca.pool.ntp.org"};
//
////"germany":
////        {"0.de.pool.ntp.org",
////        "1.de.pool.ntp.org",
////        "2.de.pool.ntp.org",
////        "3.de.pool.ntp.org"};
//
////"syngapore":
////        {"0.sg.pool.ntp.org",
////        "1.sg.pool.ntp.org",
////        "2.sg.pool.ntp.org",
////        "3.sg.pool.ntp.org"};
//
////"australia":
////        {"0.oceania.pool.ntp.org",
////        "1.oceania.pool.ntp.org",
////        "2.oceania.pool.ntp.org",
////        "3.oceania.pool.ntp.org"};
//
////"japan":
////        {"0.jp.pool.ntp.org",
////        "1.jp.pool.ntp.org",
////        "2.jp.pool.ntp.org",
////        "3.jp.pool.ntp.org"};
//
////"asia":
////        {"0.asia.pool.ntp.org",
////        "1.asia.pool.ntp.org",
////        "2.asia.pool.ntp.org",
////        "3.asia.pool.ntp.org"};
//
//// "south_america":
////        {"0.south-america.pool.ntp.org",
////         "1.south-america.pool.ntp.org",
////         "2.south-america.pool.ntp.org",
////         "3.south-america.pool.ntp.org"};


#endif //CHRONOS_C_CHRONOS_H
