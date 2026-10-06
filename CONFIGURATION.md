# Firmware image configuration

The firmware contains a 356-byte, versioned configuration table in application
flash. `tools/configure_image.py` finds its unique marker, checks the table and
its CRC-32, changes requested values, then updates both the table CRC and the
checksums of affected Motorola S-records. No configuration sector, bootloader
change, or NVM allocation is required.

The image table defines factory settings. The runtime update interval also has
an NVM3 override, described below; the other settings remain image-only.

Launch the graphical editor with Python's standard Tk interface:

```sh
python3 tools/configure_image.py --gui results/bms_sensor.s37
```

The same operations are available from the command line:

```sh
python3 tools/configure_image.py results/bms_sensor.s37 --show
python3 tools/configure_image.py results/bms_sensor.s37 \
  --set serial_tx_location=18 \
  --set serial_rx_location=18 \
  --set bms_address=1 \
  --set zigbee_primary_mask=0x02000000 \
  --set zigbee_secondary_mask=0 \
  --set sample_interval_s=60 \
  -o results/bms_sensor-configured.s37
```

The input remains unchanged unless `--in-place` is explicitly used. Both flat
`.bin` files and `.s37`, `.srec`, or `.s19` Motorola S-record files are
supported. The build places both `results/bms_sensor.s37` and
`results/bms_sensor.bin` in the results directory. Flash the resulting image
with the same address and procedure as the normal build output.

## Settings

| Key | Default | Allowed values |
| --- | ---: | --- |
| `serial_tx_location` | 18 (PD10) | USART0 TX location 0 through 31 |
| `serial_rx_location` | 19 (PD12) | USART0 RX location 0 through 31 |
| `bms_address` | 1 | DALY logical address 1 through 15 |
| `zigbee_primary_mask` | `0x0318c800` | Bit mask for channels 11 through 26 |
| `zigbee_secondary_mask` | `0x04e73000` | Bit mask for channels 11 through 26 |
| `sample_interval_s` | 30 | 5 through 3600 seconds |
| `zigbee_long_poll_ms` | 3000 | 1000 through 60000 milliseconds |
| `network_loss_timeout_h` | 24 | 1 through 720 hours |
| `serial_timeout_ms` | 1000 | 100 through 5000 milliseconds |

At least one channel must be enabled across the two Zigbee masks. A channel is
selected by bit `1 << channel`; for example, channel 25 alone is `0x02000000`.
The primary mask is searched first and the secondary mask afterward.

TX and RX locations are independent. The GUI presents GPIO names while the
command line uses the location numbers below:

| Locations | USART0 TX GPIOs | USART0 RX GPIOs |
| --- | --- | --- |
| 0–5 | PA0–PA5 | PA1–PA5, then PB11 at location 5 |
| 6–10 | PB11–PB15 | PB12–PB15, then PC6 at location 10 |
| 11–16 | PC6–PC11 | PC7–PC11, then PD9 at location 16 |
| 17–23 | PD9–PD15 | PD10–PD15, then PF0 at location 23 |
| 24–30 | PF0–PF6 | PF1–PF7 |
| 31 | PF7 | PA0 |

The default TX location 18 and RX location 19 select PD10 and PD12.
For example, TX location 18 and RX location 18 select PD10 and PD11;
locations 19 and 19 select PD11 and PD12. Some different location numbers map
to the same GPIO: TX location 1 and RX location 0 both select PA1. The tool and
firmware reject any combination that assigns TX and RX to the same physical pin.

The firmware validates the marker, version, size, keys, ranges, serial-pin
combination, channel masks, and CRC at every boot. It uses the compiled defaults
for the entire table if validation fails, avoiding partial or unsafe settings
after corruption.

Patch an application image before converting it to a signed GBL or OTA file.
Changing a signed GBL or OTA payload afterward invalidates its signature and
container integrity checks. An OTA update replaces these image settings with
the settings embedded in the new application, so configure each upgrade image
before packaging it.

## Runtime update interval

Endpoint 1 has a standard **Analog Value (Basic)** server cluster (`0x000E`),
whose Description (`0x001C`) is **Update interval**. Its writable PresentValue
(`0x0055`) is a ZCL single-precision float (`0x39`) measured in seconds;
EngineeringUnits (`0x0075`) is 73, and Resolution (`0x006A`) is 1 second.

Use ZHA's device **Manage Zigbee device** attribute editor to write PresentValue
as a whole number from 5 to 3600. Fractions, NaN, infinities and out-of-range
values are rejected with `INVALID_VALUE`. All BMS measurement attributes remain
read-only. Home Assistant may need a fresh device interview to discover the
added cluster after upgrading existing hardware.

On first boot, the application seeds NVM3 key `0x0B502` from the validated
`sample_interval_s` image-table value. Later boots restore the saved interval.
Each accepted change is committed before the Zigbee write is acknowledged;
a storage failure returns `FAILURE` and leaves the live interval unchanged.
Writing the current value avoids a redundant flash write. Invalid saved values
are replaced with the image default; other read errors use the default for the
current boot without overwriting storage.

Changes reschedule the next sample within one second, allowing any active BMS
read cycle to finish. A new image's default does not replace an existing NVM3
override. Network removal and automatic network recovery retain the override;
erasing application NVRAM restores the image-table default on the next boot.

## Flashing with ST-Link and pyOCD

Flashing support is optional. The configurator imports the open-source pyOCD
package only after `--flash` or the GUI's **Save and flash** button is used.
Install pyOCD and the exact EFR32MG1B device pack once:

```sh
python3 -m pip install pyocd
pyocd pack update
pyocd pack install EFR32MG1B232F256GM48
```

The public pack is
`SiliconLabs.GeckoPlatform_EFR32MG1B_DFP` version 4.4.0. It identifies the exact
`EFR32MG1B232F256GM48` target and contains the `GECKOP2.FLM` flash algorithm.
Current pyOCD releases include the ST-Link probe backend.

Flash an existing configured image with:

```sh
python3 tools/configure_image.py results/bms_sensor.bin --flash
```

Configuration and flashing can be performed together:

```sh
python3 tools/configure_image.py results/bms_sensor.s37 \
  --set serial_tx_location=18 \
  --set serial_rx_location=18 \
  -o results/bms-pd10-pd11.s37 \
  --flash
```

Both binary and S-record inputs are accepted. Contiguous S-record regions are
passed to pyOCD as separate addressed segments, so gaps are not written and the
source file is not converted or changed. Before opening pyOCD, the tool validates
the image configuration and ensures every segment lies within the MCU's 256 KiB
flash.

The programmer selection is restricted to pyOCD's `stlink:` backend. It cannot
silently select a connected J-Link or CMSIS-DAP probe. With more than one
ST-Link, pass a full or partial serial number using `--probe`. Useful additional
options are:

```sh
--frequency 1000000
--connect-mode under-reset
--pack /path/to/SiliconLabs.GeckoPlatform_EFR32MG1B_DFP.4.4.0.pack
```

The default connection mode is `halt`; `under-reset` requires the ST-Link NRST
connection. Connect SWDIO, SWCLK, ground, and target-voltage reference. The
target remains powered by its normal supply unless the particular board and
probe wiring are intentionally designed otherwise.

The backend requests sector erase, so it programs only sectors covered by the
application image and does not request a full-chip erase. The GUI displays a
confirmation dialog before calling pyOCD. Physical ST-Link programming remains
to be validated when that probe and target wiring are available.
