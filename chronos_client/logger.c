#include "logger.h"
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <string.h>

void logger(const char* message, char* filename) {
    time_t now;
    time(&now);
    FILE *out=fopen(filename,"a");
    char output[1000] = {0};
    snprintf(output, sizeof(output), "%s: %s\n", strtok(ctime(&now), "\n"), message);
    fputs(output, out);
    fclose(out);
}

