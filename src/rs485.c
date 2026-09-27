#include "rs485.h"
#include "bms_protocol.h"
#include "em_cmu.h"
#include "em_gpio.h"
#include "em_usart.h"
#include "sl_power_manager.h"
#include "app_config.h"

volatile struct rs485_diagnostics rs485_diag;
static volatile uint8_t ring[128];
static volatile uint8_t head;
static volatile uint8_t tail;
static struct bms_parser parser;
static uint32_t started;
static bool active;

/* Resolved USART0 locations and their physical GPIOs. */
struct serial_route {
    GPIO_Port_TypeDef tx_port;
    GPIO_Port_TypeDef rx_port;
    uint8_t tx_pin;
    uint8_t rx_pin;
    uint8_t tx_location;
    uint8_t rx_location;
};
static struct serial_route route;

/* Resolve a USART0 TX location using the EFR32MG1 alternate-function table. */
static void resolve_tx(uint8_t location)
{
    route.tx_location = location;
    if (location <= 5) {
        route.tx_port = gpioPortA;
        route.tx_pin = location;
    } else if (location <= 10) {
        route.tx_port = gpioPortB;
        route.tx_pin = location + 5;
    } else if (location <= 16) {
        route.tx_port = gpioPortC;
        route.tx_pin = location - 5;
    } else if (location <= 23) {
        route.tx_port = gpioPortD;
        route.tx_pin = location - 8;
    } else {
        route.tx_port = gpioPortF;
        route.tx_pin = location - 24;
    }
}

/* Resolve a USART0 RX location using the EFR32MG1 alternate-function table. */
static void resolve_rx(uint8_t location)
{
    route.rx_location = location;
    if (location <= 4) {
        route.rx_port = gpioPortA;
        route.rx_pin = location + 1;
    } else if (location <= 9) {
        route.rx_port = gpioPortB;
        route.rx_pin = location + 6;
    } else if (location <= 15) {
        route.rx_port = gpioPortC;
        route.rx_pin = location - 4;
    } else if (location <= 22) {
        route.rx_port = gpioPortD;
        route.rx_pin = location - 7;
    } else if (location <= 30) {
        route.rx_port = gpioPortF;
        route.rx_pin = location - 23;
    } else {
        route.rx_port = gpioPortA;
        route.rx_pin = 0;
    }
}

/* Capture bytes promptly while Zigbee runs in the main loop. */
void USART0_RX_IRQHandler(void)
{
    uint32_t flags = USART_IntGet(USART0);
    USART_IntClear(USART0, flags);
    if (flags & (USART_IF_RXOF | USART_IF_FERR | USART_IF_PERR))
        rs485_diag.uart_errors++;
    while (USART0->STATUS & USART_STATUS_RXDATAV) {
        uint8_t byte = USART_Rx(USART0);
        uint8_t next = (head + 1) & 127;
        rs485_diag.received++;
        if (next == tail) {
            rs485_diag.overruns++;
        } else {
            ring[head] = byte;
            head = next;
        }
    }
}

/* Configure independently selected and validated USART0 TX and RX locations. */
void rs485_init(void)
{
    resolve_tx(app_config_get(APP_CONFIG_SERIAL_TX_LOCATION));
    resolve_rx(app_config_get(APP_CONFIG_SERIAL_RX_LOCATION));
    CMU_ClockEnable(cmuClock_GPIO, true);
    GPIO_PinModeSet(route.rx_port, route.rx_pin, gpioModeInputPull, 1);
    GPIO_PinModeSet(route.tx_port, route.tx_pin, gpioModePushPull, 1);
}

/* Hold EM1 only while USART is required; automatic direction needs no DE pin. */
void rs485_start(uint8_t group, uint32_t now_ms)
{
    sl_power_manager_add_em_requirement(SL_POWER_MANAGER_EM1);
    CMU_ClockEnable(cmuClock_USART0, true);
    USART_InitAsync_TypeDef config = USART_INITASYNC_DEFAULT;
    config.baudrate = 9600;
    USART_InitAsync(USART0, &config);
    USART0->ROUTELOC0 = (route.tx_location << _USART_ROUTELOC0_TXLOC_SHIFT)
                        | (route.rx_location << _USART_ROUTELOC0_RXLOC_SHIFT);
    USART0->ROUTEPEN = USART_ROUTEPEN_TXPEN | USART_ROUTEPEN_RXPEN;
    head = tail = 0;
    bms_parser_init(&parser, group);
    USART_IntClear(USART0, _USART_IF_MASK);
    USART_IntEnable(USART0, USART_IEN_RXDATAV | USART_IEN_RXOF |
                           USART_IEN_FERR | USART_IEN_PERR);
    NVIC_ClearPendingIRQ(USART0_RX_IRQn);
    NVIC_EnableIRQ(USART0_RX_IRQn);
    started = now_ms;
    active = true;
    uint8_t request[8];
    bms_request(group, request);
    rs485_diag.requests++;
    for (unsigned i = 0; i < sizeof(request); i++)
        USART_Tx(USART0, request[i]);
}

/* Finish after a CRC-valid response or configured timeout, then permit EM2. */
bool rs485_process(uint32_t now_ms)
{
    if (!active)
        return true;
    int result = 0;
    while (tail != head && result == 0) {
        uint8_t byte = ring[tail];
        tail = (tail + 1) & 127;
        result = bms_parser_feed(&parser, byte);
    }
    if (result == 0 && (uint32_t)(now_ms - started)
        < (uint32_t)app_config_get(APP_CONFIG_SERIAL_TIMEOUT_MS))
        return false;
    if (result > 0)
        rs485_diag.replies++;
    else if (result < 0)
        rs485_diag.exceptions++;
    else
        rs485_diag.timeouts++;
    NVIC_DisableIRQ(USART0_RX_IRQn);
    USART_Enable(USART0, usartDisable);
    USART0->ROUTEPEN = 0;
    CMU_ClockEnable(cmuClock_USART0, false);
    sl_power_manager_remove_em_requirement(SL_POWER_MANAGER_EM1);
    active = false;
    return true;
}
