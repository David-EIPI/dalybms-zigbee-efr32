#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source "${EFR32_ENV:-/opt/silabs/efr32mg1-2026-09/env.sh}"
mkdir -p results
# SLC reuses old configuration headers. Generate from a clean output directory.
if [ -d build ]; then
    rm -rf build
fi
python3 tools/generate.py
slc generate firmware/bms.slcp -np -d build -name=bms_sensor -o makefile > results/generation.log 2>&1
zap-cli generate -i firmware/config/zcl/zcl_config.zap -z firmware/config/zcl/zcl-properties.json -g "$GSDK/protocol/zigbee/app/framework/gen-template/gen-templates.json" -o build/autogen --packageMatch strict --stateDirectory /tmp/bms-zap-state > results/zap-generation.log 2>&1
python3 tools/fix_layout.py
python3 tools/check_generated.py
cp src/app_config.[ch] src/bms_protocol.[ch] src/rs485.[ch] src/bms_metrics*.[ch] src/zigbee.[ch] src/supply.[ch] firmware/main.c firmware/app.c build/
make -C build -f bms_sensor.Makefile release ARM_GCC_DIR="$ARM_GCC_DIR" -j4 > results/build.log 2>&1
arm-none-eabi-size build/build/release/bms_sensor.out > results/size.txt
cp build/build/release/bms_sensor.s37 results/bms_sensor.s37
cp build/build/release/bms_sensor.bin results/bms_sensor.bin
