#include "settings.h"
#include "app_config.h"
#include "nvm3_default.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

void *nvm3_defaultHandle;
static uint32_t stored;
static uint32_t factory_default = 30;
static unsigned writes;
static bool exists;
static bool read_failure;
static bool write_failure;

/* Supply a patchable factory value independently of the NVRAM mock. */
int32_t app_config_get(enum app_config_key key)
{
    assert(key == APP_CONFIG_SAMPLE_INTERVAL_S);
    return factory_default;
}

/* Simulate absent, persisted and failing storage across application restarts. */
Ecode_t nvm3_readData(void *handle, uint32_t key, void *value, size_t size)
{
    (void)handle;
    assert(key == SETTINGS_INTERVAL_KEY && size == sizeof(stored));
    if (read_failure)
        return 2;
    if (!exists)
        return ECODE_NVM3_ERR_KEY_NOT_FOUND;
    memcpy(value, &stored, size);
    return ECODE_NVM3_OK;
}

/* Count successful commits and model a failed flash write. */
Ecode_t nvm3_writeData(void *handle, uint32_t key, const void *value, size_t size)
{
    (void)handle;
    assert(key == SETTINGS_INTERVAL_KEY && size == sizeof(stored));
    if (write_failure)
        return 2;
    memcpy(&stored, value, size);
    exists = true;
    writes++;
    return ECODE_NVM3_OK;
}

/* Verify default seeding, reboot retention, validation and atomic failures. */
int main(void)
{
    factory_default = 45;
    assert(settings_init());
    assert(settings_interval_s() == 45 && stored == 45 && writes == 1);
    assert(settings_set_interval(60));
    assert(settings_interval_s() == 60 && stored == 60 && writes == 2);
    assert(settings_set_interval(60) && writes == 2);
    factory_default = 90;
    assert(settings_init());
    assert(settings_interval_s() == 60 && writes == 2);

    float invalid[] = {0, 4, 3601, -1, 5.5f, NAN, INFINITY, -INFINITY};
    for (unsigned i = 0; i < sizeof(invalid) / sizeof(invalid[0]); i++) {
        assert(!settings_interval_valid(invalid[i]));
        assert(!settings_set_interval(invalid[i]));
    }
    assert(settings_interval_s() == 60 && stored == 60 && writes == 2);
    write_failure = true;
    assert(!settings_set_interval(120));
    assert(settings_interval_s() == 60 && stored == 60);
    write_failure = false;
    assert(settings_set_interval(5));
    assert(settings_set_interval(3600));
    assert(settings_init() && settings_interval_s() == 3600);

    stored = 0;
    assert(settings_init() && settings_interval_s() == 90 && stored == 90);
    read_failure = true;
    unsigned count = writes;
    assert(!settings_init());
    assert(settings_interval_s() == 90 && writes == count);
    read_failure = false;
    exists = false;
    write_failure = true;
    assert(!settings_init() && settings_interval_s() == 90);
    assert(!settings_set_interval(90));
    write_failure = false;
    assert(settings_set_interval(90) && exists && stored == 90);
    puts("persistent sampling settings tests passed");
}
