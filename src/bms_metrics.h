#ifndef BMS_METRICS_H
#define BMS_METRICS_H
#include <stdbool.h>
#include <stdint.h>
/* Compact description of a measurement and its standard ZCL destination. */
struct bms_metric {
    float scale;
    int16_t offset;
    uint16_t reg, mask, cluster, attribute, divisor;
    uint8_t endpoint, kind, shift, special;
};
enum bms_metric_kind { METRIC_VOLTAGE, METRIC_CURRENT, METRIC_POWER, METRIC_TEMPERATURE, METRIC_ANALOG, METRIC_BINARY };
#define BMS_METRIC_COUNT 130
extern const struct bms_metric bms_metrics[BMS_METRIC_COUNT];
bool bms_metric_value(const struct bms_metric *metric, float *value);
#endif
