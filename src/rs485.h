#ifndef BMS_RS485_H
#define BMS_RS485_H
#include <stdbool.h>
#include <stdint.h>

/* SWD-visible transport counters; no diagnostic traffic uses the BMS UART. */
struct rs485_diagnostics {
    uint32_t requests;
    uint32_t received;
    uint32_t replies;
    uint32_t timeouts;
    uint32_t exceptions;
    uint32_t uart_errors;
    uint32_t overruns;
};
extern volatile struct rs485_diagnostics rs485_diag;
void rs485_init(void);
void rs485_start(uint8_t group, uint32_t now_ms);
bool rs485_process(uint32_t now_ms);
#endif
