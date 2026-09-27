#include "zigbee.h"
#include "bms_metrics.h"
#include "app/framework/include/af.h"
#include "app/framework/plugin/network-steering/network-steering.h"
#include "sl_power_manager.h"
#include "nvm3_default.h"
#include "app_config.h"
#include <math.h>
#include <string.h>

volatile struct zigbee_diagnostics zigbee_diag;
static uint32_t interview_until;
static uint32_t next_join;
static uint32_t network_loss_started;
static uint32_t next_leave_attempt;
static bool configuration_ready;
static bool network_loss_active;
static bool network_reset_pending;
/* Application-owned NVM3 user-domain key; Zigbee tokens use domain 0x10000. */
#define LAYOUT_VERSION_KEY 0x0b501UL
#define LAYOUT_VERSION 0x424d5302UL
#define INTERVIEW_TASK 0x10000UL
#define LEAVE_RETRY_MS 1000UL

/* Keep fast parent polls and EM1 available during initial ZHA interviewing. */
static void interview_start(uint32_t now)
{
    if (!zigbee_diag.interview) {
        sl_power_manager_add_em_requirement(SL_POWER_MANAGER_EM1);
        emberAfAddToCurrentAppTasks(INTERVIEW_TASK);
    }
    zigbee_diag.interview = 1;
    interview_until = now + 300000;
}

/* Apply an attribute value through the SDK so configured reporting detects it. */
static void write_value(uint8_t ep, uint16_t cluster, uint16_t attr,
                        const void *value, uint8_t type)
{
    uint8_t previous[4];
    uint8_t size = emberAfGetDataSize(type);
    if (size <= sizeof(previous)
        && emberAfReadServerAttribute(ep, cluster, attr, previous, sizeof(previous))
           == EMBER_ZCL_STATUS_SUCCESS
        && memcmp(previous, value, size) == 0)
        return;
    if (emberAfWriteServerAttribute(ep, cluster, attr, (uint8_t *)value, type)
        != EMBER_ZCL_STATUS_SUCCESS)
        zigbee_diag.attribute_errors++;
}

/* Populate standard clusters, including their explicit invalid-value encodings. */
void zigbee_update(void)
{
    for (unsigned i = 0; i < BMS_METRIC_COUNT; i++) {
        const struct bms_metric *m = &bms_metrics[i];
        float value;
        bool valid = bms_metric_value(m, &value);
        if (m->kind == METRIC_ANALOG || m->kind == METRIC_BINARY) {
            uint8_t reliability = valid ? 0 : 7;
            uint8_t flags = valid ? 0 : 2;
            write_value(m->endpoint, m->cluster, 0x67, &reliability, ZCL_ENUM8_ATTRIBUTE_TYPE);
            write_value(m->endpoint, m->cluster, 0x6f, &flags, ZCL_BITMAP8_ATTRIBUTE_TYPE);
        }
        if (m->kind == METRIC_ANALOG) {
            if (!valid)
                value = NAN;
            write_value(m->endpoint, m->cluster, m->attribute, &value, ZCL_FLOAT_SINGLE_ATTRIBUTE_TYPE);
        } else if (m->kind == METRIC_BINARY) {
            /* ZHA treats 0xff as true; retain the last state and flag it unreliable. */
            if (!valid)
                continue;
            uint8_t state = value != 0;
            write_value(m->endpoint, m->cluster, m->attribute, &state, ZCL_BOOLEAN_ATTRIBUTE_TYPE);
        } else {
            int16_t encoded = INT16_MIN;
            float scaled = valid ? value * m->divisor : 0;
            if (valid && scaled >= -32767 && scaled <= 32767)
                encoded = (int16_t)(scaled >= 0 ? scaled + .5f : scaled - .5f);
            write_value(m->endpoint, m->cluster, m->attribute, &encoded, ZCL_INT16S_ATTRIBUTE_TYPE);
        }
    }
    zigbee_diag.updates++;
}

/* Invalidate old endpoint bindings/reports once, preserving network credentials. */
static bool prepare_endpoint_layout(void)
{
    uint32_t version;
    Ecode_t status = nvm3_readData(nvm3_defaultHandle, LAYOUT_VERSION_KEY,
                                  &version, sizeof(version));
    if (status == ECODE_NVM3_OK && version == LAYOUT_VERSION)
        return true;
    if (status != ECODE_NVM3_OK && status != ECODE_NVM3_ERR_KEY_NOT_FOUND)
        return false;
    if (emberClearBindingTable() != EMBER_SUCCESS
        || emberAfClearReportTableCallback() != EMBER_SUCCESS)
        return false;
    version = LAYOUT_VERSION;
    return nvm3_writeData(nvm3_defaultHandle, LAYOUT_VERSION_KEY,
                         &version, sizeof(version)) == ECODE_NVM3_OK;
}

/* Remove coordinator-owned configuration before commissioning on a new network. */
static void clear_network_configuration(void)
{
    if (emberClearBindingTable() != EMBER_SUCCESS
        || emberAfClearReportTableCallback() != EMBER_SUCCESS)
        zigbee_diag.attribute_errors++;
}

/* Complete a network reset once the stack has discarded its old membership. */
static void finish_network_reset(uint32_t now)
{
    network_reset_pending = false;
    network_loss_active = false;
    zigbee_diag.network_loss_seconds = 0;
    next_join = now + LEAVE_RETRY_MS;
}

/* Leave the unreachable network and arrange fresh network steering. */
static void request_network_reset(uint32_t now)
{
    if (!network_reset_pending) {
        network_reset_pending = true;
        next_leave_attempt = now;
        zigbee_diag.network_resets++;
        clear_network_configuration();
    }
    if (emberNetworkState() == EMBER_NO_NETWORK) {
        finish_network_reset(now);
        return;
    }
    if ((int32_t)(now - next_leave_attempt) < 0)
        return;
    next_leave_attempt = now + LEAVE_RETRY_MS;
    (void)emberLeaveNetwork();
}

/* Identify an over-the-air request that explicitly removed this device. */
static bool coordinator_requested_leave(EmberLeaveReason reason,
                                        EmberNodeId source)
{
    if (source == EMBER_UNKNOWN_NODE_ID)
        return false;
    return reason == EMBER_LEAVE_DUE_TO_NWK_LEAVE_MESSAGE
           || reason == EMBER_LEAVE_DUE_TO_APS_REMOVE_MESSAGE
           || reason == EMBER_LEAVE_DUE_TO_ZDO_LEAVE_MESSAGE;
}

/* Initialize poll intervals and restore any persisted Zigbee network. */
void zigbee_init(void)
{
    configuration_ready = prepare_endpoint_layout();
    if (!configuration_ready) {
        zigbee_diag.attribute_errors++;
        return;
    }
    emberAfSetLongPollIntervalMsCallback(
        app_config_get(APP_CONFIG_LONG_POLL_MS));
    emberAfSetShortPollIntervalMsCallback(250);
    sli_zigbee_af_network_steering_set_channel_mask(
        app_config_get(APP_CONFIG_ZIGBEE_PRIMARY_MASK), false);
    sli_zigbee_af_network_steering_set_channel_mask(
        app_config_get(APP_CONFIG_ZIGBEE_SECONDARY_MASK), true);
    emberNetworkInit(NULL);
    next_join = halCommonGetInt32uMillisecondTick() + 10000;
    zigbee_update();
}

/* Rejoin until the configured limit, then discard the network and steer. */
void zigbee_process(uint32_t now)
{
    EmberNetworkStatus network_state;

    if (!configuration_ready)
        return;
    network_state = emberNetworkState();
    zigbee_diag.network_state = network_state;
    if (zigbee_diag.interview && (int32_t)(now - interview_until) >= 0) {
        zigbee_diag.interview = 0;
        emberAfRemoveFromCurrentAppTasks(INTERVIEW_TASK);
        sl_power_manager_remove_em_requirement(SL_POWER_MANAGER_EM1);
    }
    if (network_reset_pending) {
        request_network_reset(now);
        return;
    }
    if (network_state == EMBER_JOINED_NETWORK_NO_PARENT) {
        if (!network_loss_active) {
            network_loss_active = true;
            network_loss_started = now;
            zigbee_diag.network_losses++;
        }
        zigbee_diag.network_loss_seconds = (now - network_loss_started) / 1000UL;
        uint32_t timeout = 60UL * 60UL * 1000UL
                           * app_config_get(APP_CONFIG_NETWORK_LOSS_H);
        if ((uint32_t)(now - network_loss_started) >= timeout) {
            request_network_reset(now);
            return;
        }
    } else if (network_state == EMBER_JOINED_NETWORK) {
        network_loss_active = false;
        zigbee_diag.network_loss_seconds = 0;
    }
    if (network_state == EMBER_NO_NETWORK && (int32_t)(now - next_join) >= 0) {
        next_join = now + 60000;
        zigbee_diag.last_join_status = emberAfPluginNetworkSteeringStart();
    }
}

/* Restore normal operation after join and honor an explicit remote removal. */
void emberAfStackStatusCallback(EmberStatus status)
{
    uint32_t now = halCommonGetInt32uMillisecondTick();

    if (status == EMBER_NETWORK_UP) {
        zigbee_diag.joins++;
        network_loss_active = false;
        network_reset_pending = false;
        zigbee_diag.network_loss_seconds = 0;
        interview_start(now);
        zigbee_update();
    } else if (status == EMBER_NETWORK_DOWN) {
        EmberNodeId source;
        EmberLeaveReason reason = emberGetLastLeaveReason(&source);

        zigbee_diag.last_leave_reason = reason;
        if (coordinator_requested_leave(reason, source))
            request_network_reset(now);
        else if (network_reset_pending && emberNetworkState() == EMBER_NO_NETWORK)
            finish_network_reset(now);
    }
}

/* Expose the actual steering result without requiring a debug console. */
void emberAfPluginNetworkSteeringCompleteCallback(EmberStatus status,
                                                  uint8_t beacons,
                                                  uint8_t attempts,
                                                  uint8_t state)
{
    (void)beacons;
    (void)attempts;
    (void)state;
    zigbee_diag.last_join_status = status;
}

/* Extend for commissioning requests; periodic ZHA reads must not prevent sleep. */
bool emberAfPreCommandReceivedCallback(EmberAfClusterCommand *command)
{
    zigbee_diag.commands_received++;
    if (zigbee_diag.interview && !command->clusterSpecific
        && command->direction == ZCL_DIRECTION_CLIENT_TO_SERVER
        && (command->commandId == ZCL_CONFIGURE_REPORTING_COMMAND_ID
            || command->commandId == ZCL_READ_REPORTING_CONFIGURATION_COMMAND_ID
            || command->commandId == ZCL_DISCOVER_ATTRIBUTES_COMMAND_ID
            || command->commandId == ZCL_DISCOVER_ATTRIBUTES_EXTENDED_COMMAND_ID
            || command->commandId == ZCL_DISCOVER_COMMANDS_RECEIVED_COMMAND_ID
            || command->commandId == ZCL_DISCOVER_COMMANDS_GENERATED_COMMAND_ID)) {
        uint32_t deadline = halCommonGetInt32uMillisecondTick() + 120000;
        if ((int32_t)(deadline - interview_until) > 0)
            interview_until = deadline;
    }
    return false;
}

/* This sensor exposes observations; remote writes never control the BMS. */
EmberAfAttributeWritePermission emberAfAllowNetworkWriteAttributeCallback(
    uint8_t endpoint, EmberAfClusterId cluster, EmberAfAttributeId attribute,
    uint8_t mask, uint16_t manufacturer, uint8_t *value, uint8_t type)
{
    (void)endpoint;
    (void)cluster;
    (void)attribute;
    (void)mask;
    (void)manufacturer;
    (void)value;
    (void)type;
    return EMBER_ZCL_ATTRIBUTE_WRITE_PERMISSION_DENY_WRITE;
}

/* Preserve the SDK's normal radio calibration callback. */
void emberAfRadioNeedsCalibratingCallback(void)
{
    sl_mac_calibrate_current_channel();
}

/* Count acknowledged standard attribute reports separately from local updates. */
bool emberAfMessageSentCallback(EmberOutgoingMessageType type,
                               uint16_t destination, EmberApsFrame *aps,
                               uint16_t length, uint8_t *message,
                               EmberStatus status)
{
    (void)type;
    (void)destination;
    if (aps->profileId == 0x0104 && length >= 3
        && (message[0] & (ZCL_FRAME_CONTROL_FRAME_TYPE_MASK
                         | ZCL_MANUFACTURER_SPECIFIC_MASK)) == 0
        && message[2] == ZCL_REPORT_ATTRIBUTES_COMMAND_ID
        && (aps->options & EMBER_APS_OPTION_RETRY)) {
        zigbee_diag.last_report_status = status;
        if (status == EMBER_SUCCESS)
            zigbee_diag.reports_acked++;
        else
            zigbee_diag.reports_failed++;
    }
    return false;
}
