#ifndef BMS_APP_CONFIG_H
#define BMS_APP_CONFIG_H

#include <stdbool.h>
#include <stdint.h>

/* Stable indices for values stored in the host-patchable flash table. */
enum app_config_key {
    APP_CONFIG_SERIAL_TX_LOCATION,
    APP_CONFIG_SERIAL_RX_LOCATION,
    APP_CONFIG_BMS_ADDRESS,
    APP_CONFIG_ZIGBEE_PRIMARY_MASK,
    APP_CONFIG_ZIGBEE_SECONDARY_MASK,
    APP_CONFIG_SAMPLE_INTERVAL_S,
    APP_CONFIG_LONG_POLL_MS,
    APP_CONFIG_NETWORK_LOSS_H,
    APP_CONFIG_SERIAL_TIMEOUT_MS,
    APP_CONFIG_COUNT
};

void app_config_init(void);
int32_t app_config_get(enum app_config_key key);
bool app_config_is_valid(void);

#endif
