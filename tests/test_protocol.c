#include "bms_protocol.h"
#include <assert.h>
#include <stdio.h>

/* Feed one complete frame to the incremental parser. */
static int feed(struct bms_parser *p, const uint8_t *data, unsigned count)
{
    int result = 0;
    for (unsigned i = 0; i < count; i++)
        result = bms_parser_feed(p, data[i]);
    return result;
}

/* Exercise real framing, noise/echo rejection, corrupt CRC and exceptions. */
int main(void)
{
    struct bms_parser p;
    uint8_t request[8];
    bms_request(0, request);
    assert(bms_crc(request, 8) == 0 && request[0] == 0x81);
    bms_set_address(3);
    bms_request(0, request);
    assert(bms_crc(request, 8) == 0 && request[0] == 0x83);
    bms_set_address(1);
    bms_parser_init(&p, 0);
    assert(feed(&p, request, 8) == 0);
    uint8_t reply[21] = { 0x51, 3, 16 };
    for (unsigned i = 0; i < 8; i++) {
        reply[3 + 2 * i] = 0x0c;
        reply[4 + 2 * i] = 0xe4 + i;
    }
    uint16_t crc = bms_crc(reply, 19);
    reply[19] = crc;
    reply[20] = crc >> 8;
    assert(feed(&p, reply, 21) == 1);
    uint16_t value;
    assert(bms_get(0, &value) && value == 3300);
    assert(bms_get(7, &value) && value == 3307);
    assert(!bms_get(8, &value));
    bms_parser_init(&p, 0);
    reply[20] ^= 1;
    assert(feed(&p, reply, 21) == 0 && !bms_get(0, &value));
    reply[20] ^= 1;
    assert(feed(&p, reply, 21) == 1);
    bms_parser_init(&p, 4);
    uint8_t exception[5] = { 0x51, 0x83, 2 };
    crc = bms_crc(exception, 3);
    exception[3] = crc;
    exception[4] = crc >> 8;
    assert(feed(&p, exception, 5) == -1);
    assert(bms_blocks[4].exception == 2 && !bms_blocks[4].valid);
    bms_parser_init(&p, 0);
    for (unsigned i = 0; i < 10000; i++)
        bms_parser_feed(&p, (uint8_t)(i * 19));
    assert(feed(&p, reply, 21) == 1);
    puts("protocol tests passed");
}
