#include "sl_system_init.h"
#include "sl_system_process_action.h"
#include "sl_power_manager.h"
#include "app/framework/include/af.h"
#include "rs485.h"
#include "bms_protocol.h"
#include "zigbee.h"
#include "supply.h"
#include "app_config.h"

static sl_zigbee_event_t poll_event;
static uint8_t group;
static bool pending;
static uint32_t next_cycle;

/* Schedule short RX service intervals and the configured measurement cadence. */
static void poll_handler(sl_zigbee_event_t *event)
{
    uint32_t now = halCommonGetInt32uMillisecondTick();
    zigbee_process(now);
    if (!pending && group == 0 && (int32_t)(now - next_cycle) < 0) {
        sl_zigbee_event_set_delay_ms(event, 1000);
        return;
    }
    if (!pending) {
        if (group == 0)
            next_cycle = now + 1000UL
                         * app_config_get(APP_CONFIG_SAMPLE_INTERVAL_S);
        rs485_start(group, now);
        pending = true;
    } else if (rs485_process(now)) {
        pending = false;
        if (++group == BMS_GROUP_COUNT) {
            group = 0;
            zigbee_diag.cycles++;
            zigbee_update();
        }
    }
    sl_zigbee_event_set_delay_ms(event, 30);
}

/* Qualify supply before persistent writes, then run the SDK cooperative loop. */
int main(void)
{
    supply_init();
    sl_system_init();
    supply_init();
    app_config_init();
    bms_set_address(app_config_get(APP_CONFIG_BMS_ADDRESS));
    rs485_init();
    zigbee_init();
    sl_zigbee_event_init(&poll_event, poll_handler);
    sl_zigbee_event_set_delay_ms(&poll_event, 100);
    while (1) {
        sl_system_process_action();
        sl_power_manager_sleep();
    }
}
