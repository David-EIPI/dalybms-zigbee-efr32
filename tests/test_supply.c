#include "supply.h"
#include "em_emu.h"
#include "em_msc.h"
#include <assert.h>
#include <stdio.h>

static MSC_TypeDef controller;
MSC_TypeDef *MSC = &controller;
static unsigned readiness_checks, voltage_checks, low_checks;
static unsigned resets, temperature_irqs;
static uint32_t flags;
static bool interrupt_enabled;
void EMU_IRQHandler(void);

/* Model readiness followed by a configurable number of undervoltage samples. */
void EMU_VmonHystInit(const EMU_VmonHystInit_TypeDef *config)
{
    assert(config->fallThreshold == 2400 && config->riseThreshold == 2600);
}
bool EMU_VmonStatusGet(void) { return ++readiness_checks > 1; }
bool EMU_VmonChannelStatusGet(unsigned channel)
{
    assert(channel == emuVmonChannel_AVDD);
    return ++voltage_checks > low_checks;
}
uint32_t EMU_IntGet(void) { return flags; }
void EMU_IntClear(uint32_t value) { flags &= ~value; }
void EMU_IntEnable(uint32_t value)
{
    assert(value == EMU_IEN_VMONAVDDFALL);
    interrupt_enabled = true;
}
void NVIC_SetPriority(unsigned irq, unsigned priority)
{
    assert(irq == EMU_IRQn && priority == 0);
}
void NVIC_EnableIRQ(unsigned irq) { assert(irq == EMU_IRQn); }
void NVIC_SystemReset(void) { resets++; }
void __DSB(void) { }
void TEMPDRV_IRQHandler(void) { temperature_irqs++; }

/* A healthy supply proceeds; undervoltage waits and disables writes on a fall. */
int main(void)
{
    supply_init();
    assert(readiness_checks == 2 && voltage_checks == 1 && interrupt_enabled);
    readiness_checks = voltage_checks = 0;
    low_checks = 2;
    supply_init();
    assert(voltage_checks == 3);
    MSC->WRITECTRL = MSC_WRITECTRL_WREN;
    flags = EMU_IF_VMONAVDDFALL;
    EMU_IRQHandler();
    assert(!(MSC->WRITECTRL & MSC_WRITECTRL_WREN) && resets == 1);
    flags = 0;
    EMU_IRQHandler();
    assert(resets == 1 && temperature_irqs == 2);
    puts("supply supervision tests passed");
}
