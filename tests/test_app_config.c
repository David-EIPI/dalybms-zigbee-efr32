#include "app_config.h"
#include <assert.h>
#include <stdio.h>

/* Confirm the compiled table layout, checksum, and defaults agree. */
int main(void)
{
    app_config_init();
    assert(app_config_is_valid());
    assert(app_config_get(APP_CONFIG_SERIAL_TX_LOCATION) == 18);
    assert(app_config_get(APP_CONFIG_SERIAL_RX_LOCATION) == 19);
    assert(app_config_get(APP_CONFIG_BMS_ADDRESS) == 1);
    assert(app_config_get(APP_CONFIG_ZIGBEE_PRIMARY_MASK) == 0x0318c800);
    assert(app_config_get(APP_CONFIG_ZIGBEE_SECONDARY_MASK) == 0x04e73000);
    assert(app_config_get(APP_CONFIG_SAMPLE_INTERVAL_S) == 30);
    assert(app_config_get(APP_CONFIG_LONG_POLL_MS) == 3000);
    assert(app_config_get(APP_CONFIG_NETWORK_LOSS_H) == 24);
    assert(app_config_get(APP_CONFIG_SERIAL_TIMEOUT_MS) == 1000);
    puts("application configuration tests passed");
}
