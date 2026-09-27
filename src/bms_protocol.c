#include "bms_protocol.h"
#include <string.h>

/* Keep requests small and preserve the status/power register relationship. */
const struct bms_query bms_queries[BMS_GROUP_COUNT] = {
    { 0x00, 8 }, { 0x30, 24 }, { 0x48, 21 }, { 0x6d, 7 },
    { 0x121, 2 }, { 0x5e, 1 }, { 0x64, 1 }, { 0x66, 4 }
};
struct bms_block bms_blocks[BMS_GROUP_COUNT];
static uint8_t request_address = 0x81;
static uint8_t response_address = 0x51;

/* Modbus CRC16, transmitted least significant byte first. */
uint16_t bms_crc(const uint8_t *bytes, size_t length)
{
    uint16_t crc = 0xffff;
    while (length--) {
        crc ^= *bytes++;
        for (unsigned bit = 0; bit < 8; bit++)
            crc = (crc >> 1) ^ ((crc & 1) ? 0xa001 : 0);
    }
    return crc;
}

/* Select the DALY logical address used for subsequent requests and replies. */
void bms_set_address(uint8_t address)
{
    if (address < 1 || address > 15)
        address = 1;
    request_address = 0x80 | address;
    response_address = 0x50 | address;
}

/* Build a function-3 request for the configured DALY board address. */
void bms_request(uint8_t group, uint8_t request[8])
{
    const struct bms_query *query = &bms_queries[group];
    request[0] = request_address;
    request[1] = 3;
    request[2] = query->first >> 8;
    request[3] = query->first;
    request[4] = 0;
    request[5] = query->count;
    uint16_t crc = bms_crc(request, 6);
    request[6] = crc;
    request[7] = crc >> 8;
}

/* Invalidate a block until a complete fresh response is accepted. */
void bms_parser_init(struct bms_parser *parser, uint8_t group)
{
    parser->used = 0;
    parser->group = group;
    bms_blocks[group].valid = 0;
    bms_blocks[group].exception = 0;
}

/* Return 1 for a valid reply, -1 for an exception, 0 while collecting/resyncing. */
int bms_parser_feed(struct bms_parser *parser, uint8_t byte)
{
    parser->bytes[parser->used++] = byte;
    while (parser->used) {
        uint8_t *p = parser->bytes;
        unsigned count = bms_queries[parser->group].count;
        unsigned length = 2 * count + 5;
        if (p[0] != response_address)
            goto discard;
        if (parser->used < 2)
            return 0;
        if (p[1] == 0x83)
            length = 5;
        else if (p[1] != 3)
            goto discard;
        if (parser->used < 3)
            return 0;
        if (p[1] == 3 && p[2] != 2 * count)
            goto discard;
        if (parser->used < length)
            return 0;
        if (bms_crc(p, length) != 0)
            goto discard;
        struct bms_block *block = &bms_blocks[parser->group];
        if (p[1] == 0x83) {
            block->exception = p[2];
            parser->used = 0;
            return -1;
        }
        for (unsigned i = 0; i < count; i++)
            block->words[i] = ((uint16_t)p[3 + 2 * i] << 8) | p[4 + 2 * i];
        block->valid = 1;
        block->successes++;
        parser->used = 0;
        return 1;
    discard:
        memmove(parser->bytes, parser->bytes + 1, --parser->used);
    }
    return 0;
}

/* Lookup only data confirmed by a valid response in the current cycle. */
bool bms_get(uint16_t address, uint16_t *value)
{
    for (unsigned i = 0; i < BMS_GROUP_COUNT; i++) {
        unsigned offset = address - bms_queries[i].first;
        if (offset < bms_queries[i].count && bms_blocks[i].valid) {
            *value = bms_blocks[i].words[offset];
            return *value != 0xffff;
        }
    }
    return false;
}
