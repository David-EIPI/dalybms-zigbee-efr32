#ifndef BMS_SUPPLY_H
#define BMS_SUPPLY_H
/* Gate startup writes until AVDD is healthy and arm a 2.4 V falling monitor. */
void supply_init(void);
#endif
