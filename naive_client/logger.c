#include "logger.h"
#include <stdio.h>
#include <time.h>
#include <string.h>

/**
 * Opens the given log file and appends the given message to it
 */
void logger(const char* message, char* filename) {
	time_t now;
	time(&now);
	FILE *out=fopen(filename,"a");
	char output[1000] = {0};
	snprintf(output, sizeof(output), "%s: %s\n", strtok(ctime(&now), "\n"), message);
	fputs(output, out);
	fclose(out);
}

