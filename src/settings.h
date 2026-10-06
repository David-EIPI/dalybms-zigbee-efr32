#ifndef BMS_SETTINGS_H
#define BMS_SETTINGS_H

#include <stdbool.h>
#include <stdint.h>

#define SETTINGS_INTERVAL_MIN 5UL
#define SETTINGS_INTERVAL_MAX 3600UL
#define SETTINGS_INTERVAL_KEY 0x0b502UL

bool settings_init(void);
bool settings_interval_valid(float seconds);
bool settings_set_interval(float seconds);
uint32_t settings_interval_s(void);

#endif
