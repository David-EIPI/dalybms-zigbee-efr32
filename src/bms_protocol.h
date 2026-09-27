#ifndef BMS_PROTOCOL_H
#define BMS_PROTOCOL_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#define BMS_GROUP_COUNT 8
#define BMS_MAX_WORDS 24

/* Read-only query blocks, including optional registers probed on this board. */
struct bms_query {
    uint16_t first;
    uint8_t count;
};
extern const struct bms_query bms_queries[BMS_GROUP_COUNT];

/* Latest response and availability for each independently queried block. */
struct bms_block {
    uint32_t successes;
    uint16_t words[BMS_MAX_WORDS];
    uint8_t valid;
    uint8_t exception;
};
extern struct bms_block bms_blocks[BMS_GROUP_COUNT];

/* Streaming response parser; excludes request echoes and checks address/CRC. */
struct bms_parser {
    uint8_t bytes[64];
    uint8_t used;
    uint8_t group;
};
uint16_t bms_crc(const uint8_t *bytes, size_t length);
void bms_set_address(uint8_t address);
void bms_request(uint8_t group, uint8_t request[8]);
void bms_parser_init(struct bms_parser *parser, uint8_t group);
int bms_parser_feed(struct bms_parser *parser, uint8_t byte);
bool bms_get(uint16_t address, uint16_t *value);
#endif
