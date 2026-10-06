#ifndef TEST_NVM3_DEFAULT_H
#define TEST_NVM3_DEFAULT_H
#include <stddef.h>
#include <stdint.h>
typedef int Ecode_t;
#define ECODE_NVM3_OK 0
#define ECODE_NVM3_ERR_KEY_NOT_FOUND 1
extern void *nvm3_defaultHandle;
Ecode_t nvm3_readData(void *handle, uint32_t key, void *value, size_t size);
Ecode_t nvm3_writeData(void *handle, uint32_t key, const void *value, size_t size);
#endif
