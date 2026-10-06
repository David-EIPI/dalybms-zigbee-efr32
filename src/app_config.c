#include "app_config.h"
#include <stddef.h>
#include <string.h>

#define CONFIG_VERSION 2UL
#define CONFIG_MARKER "BMSCFG:EFR32MG1"
#define CONFIG_KEY_LENGTH 24
#define ZIGBEE_CHANNEL_MASK 0x07fff800UL

/* A fixed-size entry lets a host tool edit values without ELF symbols. */
struct app_config_entry {
    char key[CONFIG_KEY_LENGTH];
    int32_t value;
    int32_t minimum;
    int32_t maximum;
};

/* Header and entries form the versioned block embedded in the flash image. */
struct app_config_block {
    char marker[16];
    uint32_t version;
    uint32_t size;
    uint32_t count;
    uint32_t crc32;
    struct app_config_entry entries[APP_CONFIG_COUNT];
};

static const char expected_keys[APP_CONFIG_COUNT][CONFIG_KEY_LENGTH] = {
    "serial_tx_location",
    "serial_rx_location",
    "bms_address",
    "zigbee_primary_mask",
    "zigbee_secondary_mask",
    "sample_interval_s",
    "zigbee_long_poll_ms",
    "network_loss_timeout_h",
    "serial_timeout_ms"
};

static const int32_t defaults[APP_CONFIG_COUNT] = {
    18, 19, 1, 0x0318c800, 0x04e73000, 30, 3000, 24, 1000
};

/* Kept in a named section and retained so image tools can find it by marker. */
__attribute__((section(".app_config"), used, aligned(4)))
static const struct app_config_block flash_config = {
    CONFIG_MARKER,
    CONFIG_VERSION,
    sizeof(struct app_config_block),
    APP_CONFIG_COUNT,
    0xbbcefc83,
    {
        { "serial_tx_location", 18, 0, 31 },
        { "serial_rx_location", 19, 0, 31 },
        { "bms_address", 1, 1, 15 },
        { "zigbee_primary_mask", 0x0318c800, 0, ZIGBEE_CHANNEL_MASK },
        { "zigbee_secondary_mask", 0x04e73000, 0, ZIGBEE_CHANNEL_MASK },
        { "sample_interval_s", 30, 5, 3600 },
        { "zigbee_long_poll_ms", 3000, 1000, 60000 },
        { "network_loss_timeout_h", 24, 1, 720 },
        { "serial_timeout_ms", 1000, 100, 5000 }
    }
};

/* Read through a volatile view: host tools patch this const flash object. */
#define live_config (*(const volatile struct app_config_block *)&flash_config)

static bool config_valid;

_Static_assert(sizeof(struct app_config_entry) == 36, "configuration entry layout");
_Static_assert(offsetof(struct app_config_block, crc32) == 28,
               "configuration header layout");

/* Encode the physical GPIO selected by one USART0 route location. */
static uint8_t serial_pin_id(uint8_t location, bool receive)
{
    if (!receive) {
        if (location <= 5)
            return location;
        if (location <= 10)
            return 0x10 | (location + 5);
        if (location <= 16)
            return 0x20 | (location - 5);
        if (location <= 23)
            return 0x30 | (location - 8);
        return 0x50 | (location - 24);
    }
    if (location <= 4)
        return location + 1;
    if (location <= 9)
        return 0x10 | (location + 6);
    if (location <= 15)
        return 0x20 | (location - 4);
    if (location <= 22)
        return 0x30 | (location - 7);
    if (location <= 30)
        return 0x50 | (location - 23);
    return 0;
}

/* Calculate the same standard CRC-32 used by the image configuration tool. */
static uint32_t config_crc32(const volatile uint8_t *bytes, size_t length)
{
    uint32_t crc = 0xffffffffUL;

    for (size_t i = 0; i < length; i++) {
        uint8_t byte = i >= offsetof(struct app_config_block, crc32)
                       && i < offsetof(struct app_config_block, crc32) + 4
                       ? 0 : bytes[i];
        crc ^= byte;
        for (unsigned bit = 0; bit < 8; bit++)
            crc = (crc >> 1) ^ ((crc & 1) ? 0xedb88320UL : 0);
    }
    return crc ^ 0xffffffffUL;
}

/* Validate the complete table before any patched value is accepted. */
void app_config_init(void)
{
    config_valid = memcmp((const void *)live_config.marker, CONFIG_MARKER,
                          sizeof(live_config.marker)) == 0
                   && live_config.version == CONFIG_VERSION
                   && live_config.size == sizeof(live_config)
                   && live_config.count == APP_CONFIG_COUNT
                   && config_crc32((const volatile uint8_t *)&live_config,
                                   sizeof(live_config)) == live_config.crc32;
    if (!config_valid)
        return;
    for (unsigned i = 0; i < APP_CONFIG_COUNT; i++) {
        const volatile struct app_config_entry *entry = &live_config.entries[i];

        if (memcmp((const void *)entry->key, expected_keys[i], CONFIG_KEY_LENGTH) != 0
            || entry->value < entry->minimum || entry->value > entry->maximum) {
            config_valid = false;
            return;
        }
    }
    uint32_t primary = live_config.entries[APP_CONFIG_ZIGBEE_PRIMARY_MASK].value;
    uint32_t secondary = live_config.entries[APP_CONFIG_ZIGBEE_SECONDARY_MASK].value;

    if (((primary | secondary) & ~ZIGBEE_CHANNEL_MASK) != 0
        || (primary | secondary) == 0)
        config_valid = false;
    uint8_t tx = live_config.entries[APP_CONFIG_SERIAL_TX_LOCATION].value;
    uint8_t rx = live_config.entries[APP_CONFIG_SERIAL_RX_LOCATION].value;

    if (serial_pin_id(tx, false) == serial_pin_id(rx, true))
        config_valid = false;
}

/* Return a checked image setting, or its compiled default for a damaged block. */
int32_t app_config_get(enum app_config_key key)
{
    if ((unsigned)key >= APP_CONFIG_COUNT)
        return 0;
    return config_valid ? live_config.entries[key].value : defaults[key];
}

/* Report whether the embedded configuration passed all integrity checks. */
bool app_config_is_valid(void)
{
    return config_valid;
}
