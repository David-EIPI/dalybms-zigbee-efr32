#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p results
python3 -m unittest tests/test_configure_image.py
cc -std=c11 -Wall -Wextra -Werror -I src tests/test_app_config.c src/app_config.c -o results/test_app_config
./results/test_app_config
cc -std=c11 -Wall -Wextra -Werror -I tests/stubs -I src tests/test_settings.c src/settings.c -o results/test_settings
./results/test_settings
cc -std=c11 -Wall -Wextra -Werror -I src tests/test_protocol.c src/bms_protocol.c -o results/test_protocol
./results/test_protocol
cc -std=c11 -Wall -Wextra -Werror -I src tests/test_metrics.c src/bms_protocol.c src/bms_metrics.c src/bms_metrics_table.c -lm -o results/test_metrics
./results/test_metrics
