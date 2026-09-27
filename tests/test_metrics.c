#include "bms_metrics.h"
#include "bms_protocol.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>

/* Find the unique physical/source mapping needed by each conversion test. */
static const struct bms_metric *find(unsigned reg, unsigned kind, unsigned special)
{
    for (unsigned i = 0; i < BMS_METRIC_COUNT; i++) {
        const struct bms_metric *m = &bms_metrics[i];
        if (m->reg == reg && m->kind == kind && m->special == special)
            return m;
    }
    assert(0);
    return NULL;
}

/* Check actual board scales and synthetic alarm/discharge/unavailable cases. */
int main(void)
{
    for (unsigned i = 0; i < BMS_GROUP_COUNT; i++)
        bms_blocks[i].valid = 1;
    bms_blocks[1].words[8] = 263;
    bms_blocks[1].words[9] = 30004;
    bms_blocks[1].words[10] = 616;
    bms_blocks[1].words[12] = 7;
    bms_blocks[1].words[13] = 2;
    bms_blocks[0].words[0] = 3768;
    float v;
    assert(bms_metric_value(find(0x38,METRIC_VOLTAGE,0),&v) && fabsf(v-26.3f)<.001f);
    assert(bms_metric_value(find(0x39,METRIC_CURRENT,0),&v) && fabsf(v-.4f)<.001f);
    assert(!bms_metric_value(find(7,METRIC_VOLTAGE,3),&v));
    assert(!bms_metric_value(find(0x32,METRIC_TEMPERATURE,14),&v));
    bms_blocks[2].words[0] = 2;
    bms_blocks[2].words[16] = 1234;
    assert(bms_metric_value(find(0x58,METRIC_POWER,20),&v) && v == -1234);
    assert(bms_metric_value(find(0x58,METRIC_POWER,21),&v) && v == 0);
    assert(bms_metric_value(find(0x58,METRIC_POWER,22),&v) && v == 1234);
    bms_blocks[3].words[0] = 0x0200; /* First wire byte: cell OVP level 2. */
    assert(bms_metric_value(find(0x6d,METRIC_ANALOG,23),&v) && v == 2);
    assert(bms_metric_value(find(0x6d,METRIC_BINARY,25),&v) && v == 1);
    bms_blocks[3].words[0] = 0;
    bms_blocks[3].words[3] = 0x0200; /* Low SOC level 2 is warning-only. */
    assert(bms_metric_value(find(0x6d,METRIC_BINARY,25),&v) && v == 0);
    assert(bms_metric_value(find(0x6d,METRIC_BINARY,24),&v) && v == 1);
    bms_blocks[2].words[19] = 255;
    assert(!bms_metric_value(find(0x5b,METRIC_TEMPERATURE,0),&v));
    puts("metric tests passed");
}
