#ifndef TEST_EM_EMU_H
#define TEST_EM_EMU_H
#include <stdbool.h>
#include <stdint.h>
typedef struct { unsigned fallThreshold, riseThreshold; } EMU_VmonHystInit_TypeDef;
#define EMU_VMONHYSTINIT_DEFAULT {0, 0}
#define EMU_IF_VMONAVDDFALL 1
#define EMU_IF_VMONAVDDRISE 2
#define EMU_IEN_VMONAVDDFALL 1
#define EMU_IRQn 0
#define emuVmonChannel_AVDD 0
void EMU_VmonHystInit(const EMU_VmonHystInit_TypeDef *config);
bool EMU_VmonStatusGet(void);
bool EMU_VmonChannelStatusGet(unsigned channel);
uint32_t EMU_IntGet(void);
void EMU_IntClear(uint32_t flags);
void EMU_IntEnable(uint32_t flags);
void NVIC_SetPriority(unsigned irq, unsigned priority);
void NVIC_EnableIRQ(unsigned irq);
void NVIC_SystemReset(void);
void __DSB(void);
#endif
