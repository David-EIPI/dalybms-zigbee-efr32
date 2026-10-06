#include "app_config.h"
#include <stdio.h>

/* Report runtime settings so a host test can execute an optimized patched ELF. */
int main(void)
{
    app_config_init();
    printf("%d", app_config_is_valid());
    for (unsigned key = 0; key < APP_CONFIG_COUNT; key++)
        printf(" %ld", (long)app_config_get(key));
    putchar('\n');
    return 0;
}
