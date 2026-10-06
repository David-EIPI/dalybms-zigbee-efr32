#include "settings.h"
#include "app_config.h"
#include "nvm3_default.h"

static uint32_t interval_s;
static bool interval_saved;

/* Load the persisted cadence; seed missing storage from the image default. */
bool settings_init(void)
{
    uint32_t stored;
    Ecode_t status = nvm3_readData(nvm3_defaultHandle, SETTINGS_INTERVAL_KEY,
                                  &stored, sizeof(stored));

    interval_s = app_config_get(APP_CONFIG_SAMPLE_INTERVAL_S);
    interval_saved = false;
    if (status == ECODE_NVM3_OK && stored >= SETTINGS_INTERVAL_MIN
        && stored <= SETTINGS_INTERVAL_MAX) {
        interval_s = stored;
        interval_saved = true;
        return true;
    }
    if (status != ECODE_NVM3_OK && status != ECODE_NVM3_ERR_KEY_NOT_FOUND)
        return false;
    interval_saved = nvm3_writeData(nvm3_defaultHandle, SETTINGS_INTERVAL_KEY,
                                  &interval_s, sizeof(interval_s)) == ECODE_NVM3_OK;
    return interval_saved;
}

/* Accept whole seconds only; comparisons also reject NaN and infinities. */
bool settings_interval_valid(float seconds)
{
    return seconds >= SETTINGS_INTERVAL_MIN && seconds <= SETTINGS_INTERVAL_MAX
           && seconds == (float)(uint32_t)seconds;
}

/* Commit before changing the live cadence; repeated values do not wear flash. */
bool settings_set_interval(float seconds)
{
    if (!settings_interval_valid(seconds))
        return false;
    uint32_t value = (uint32_t)seconds;

    if (value == interval_s && interval_saved)
        return true;
    if (nvm3_writeData(nvm3_defaultHandle, SETTINGS_INTERVAL_KEY,
                     &value, sizeof(value)) != ECODE_NVM3_OK)
        return false;
    interval_s = value;
    interval_saved = true;
    return true;
}

/* Return the restored or successfully committed runtime sampling interval. */
uint32_t settings_interval_s(void)
{
    return interval_s;
}
