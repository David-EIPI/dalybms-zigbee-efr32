#ifndef TEST_EM_MSC_H
#define TEST_EM_MSC_H
#include <stdint.h>
typedef struct { uint32_t WRITECTRL; } MSC_TypeDef;
extern MSC_TypeDef *MSC;
#define MSC_WRITECTRL_WREN 1
#endif
