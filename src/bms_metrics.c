#include "bms_metrics.h"
#include "bms_protocol.h"

/* Aggregate every documented alarm/error bit without compiler-specific bitfields. */
static bool alarm_summary(bool errors_only)
{
    static const uint16_t error_masks[7] = {
        0x8080, 0xc0c0, 0x40c0, 0x8000, 0, 0x00ff, 0xff80
    };
    for (unsigned i = 0; i < 7; i++) {
        uint16_t raw;
        if (!bms_get(0x6d + i, &raw))
            continue;
        if (raw & error_masks[i])
            return true;
        if (i < 4) {
            for (unsigned j = 0; j < 4; j++) {
                unsigned level = (raw >> ((j / 2 ? 0 : 8) + 3 * (j % 2))) & 7;
                /* Low SOC/SOH are warnings, not protection faults. */
                if (level && (!errors_only || (level > 1 && !(i == 3 && j < 2))))
                    return true;
            }
        }
    }
    return false;
}

/* Convert validated registers to physical values; never invent absent probes. */
bool bms_metric_value(const struct bms_metric *metric, float *value)
{
    uint16_t raw, count;
    if (metric->special == 26) {
        *value = bms_blocks[0].valid && bms_blocks[1].valid && bms_blocks[2].valid;
        return true;
    }
    if (!bms_get(metric->reg, &raw))
        return false;
    if (metric->special == 3 &&
        (!bms_get(0x3c, &count) || metric->reg >= count || raw == 0))
        return false;
    if (metric->special >= 4 && metric->special <= 11 &&
        (!bms_get(0x3c, &count) || metric->special - 4 >= count))
        return false;
    if (metric->special >= 12 && metric->special <= 19 &&
        (!bms_get(0x3d, &count) || metric->special - 12 >= count))
        return false;
    if (metric->kind == METRIC_TEMPERATURE && raw == 255)
        return false;
    if (metric->special == 24 || metric->special == 25) {
        *value = alarm_summary(metric->special == 25);
        return true;
    }
    if (metric->special >= 20 && metric->special <= 22) {
        uint16_t state;
        if (!bms_get(0x48, &state) || state > 2)
            return false;
        *value = state == 0 ? 0 : (state == 1 ? raw : -(float)raw);
        if (metric->special == 21 && *value < 0)
            *value = 0;
        if (metric->special == 22)
            *value = *value < 0 ? -*value : 0;
        return true;
    }
    raw = (raw >> metric->shift) & metric->mask;
    *value = ((int32_t)raw + metric->offset) * metric->scale;
    if (metric->kind == METRIC_BINARY)
        *value = raw != 0;
    if (metric->special == 1 && *value < 0)
        *value = 0;
    if (metric->special == 2)
        *value = *value < 0 ? -*value : 0;
    return true;
}
