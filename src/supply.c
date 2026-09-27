#include "supply.h"
#include "em_emu.h"
#include "em_msc.h"
#include "tempdrv.h"

/* Stop initiating flash writes and restart through the voltage-qualified boot. */
static void supply_low(void)
{
    MSC->WRITECTRL &= ~MSC_WRITECTRL_WREN;
    __DSB();
    NVIC_SystemReset();
}

/* Share EMU interrupts with the SDK temperature compensation driver. */
void EMU_IRQHandler(void)
{
    if (EMU_IntGet() & EMU_IF_VMONAVDDFALL)
        supply_low();
    TEMPDRV_IRQHandler();
}

/* Configure calibrated VMON thresholds before any stack/NVM initialization. */
void supply_init(void)
{
    EMU_VmonHystInit_TypeDef config = EMU_VMONHYSTINIT_DEFAULT;
    config.fallThreshold = 2400;
    config.riseThreshold = 2600;
    EMU_VmonHystInit(&config);
    while (!EMU_VmonStatusGet())
        ;
    /* Poll while undervoltage: no stack, radio, serial or flash writes yet. */
    while (!EMU_VmonChannelStatusGet(emuVmonChannel_AVDD))
        ;
    EMU_IntClear(EMU_IF_VMONAVDDFALL | EMU_IF_VMONAVDDRISE);
    EMU_IntEnable(EMU_IEN_VMONAVDDFALL);
    NVIC_SetPriority(EMU_IRQn, 0);
    NVIC_EnableIRQ(EMU_IRQn);
}
