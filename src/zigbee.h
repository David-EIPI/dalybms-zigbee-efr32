#ifndef BMS_ZIGBEE_H
#define BMS_ZIGBEE_H
#include <stdint.h>

/* SWD-visible application state for joining, reports and hardware validation. */
struct zigbee_diagnostics {
    uint32_t cycles;
    uint32_t attribute_errors;
    uint32_t joins;
    uint32_t last_join_status;
    uint32_t network_state;
    uint32_t interview;
    uint32_t updates;
    uint32_t reports_acked;
    uint32_t reports_failed;
    uint32_t last_report_status;
    uint32_t commands_received;
    uint32_t network_losses;
    uint32_t network_resets;
    uint32_t last_leave_reason;
    uint32_t network_loss_seconds;
};
extern volatile struct zigbee_diagnostics zigbee_diag;
void zigbee_init(void);
void zigbee_process(uint32_t now);
void zigbee_update(void);
#endif
