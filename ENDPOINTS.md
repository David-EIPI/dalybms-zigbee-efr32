# Zigbee endpoint map

Manufacturer: DS. Model: bmssensor1. Profile: Home Automation (0x0104).
All BMS fields are read-only; Binary Input represents observed state, not a control.
Endpoint 1 additionally exposes writable Analog Value (0x000e) PresentValue (0x0055):
Update interval in whole seconds (5–3600), persisted in NVM3; EngineeringUnits is 73 (seconds).
Every endpoint has Basic ProductLabel (0x000e), identifying its electrical/temperature source.
Analog/Binary Input share endpoints independently and use Description for their field names.
Analog/Binary Input and Analog Value descriptions are populated (48/16/48-byte limits).
Optional/absent measurements retain invalid values.

## Endpoint labels

| Endpoint | ProductLabel |
|---:|---|
| 1 | Pack |
| 2 | Pack charge |
| 3 | Pack discharge |
| 4 | Balancer |
| 5 | Cell 1 |
| 6 | Cell 2 |
| 7 | Cell 3 |
| 8 | Cell 4 |
| 9 | Cell 5 |
| 10 | Cell 6 |
| 11 | Cell 7 |
| 12 | Cell 8 |
| 13 | Highest cell |
| 14 | Lowest cell |
| 15 | Cell spread |
| 16 | Probe 1 |
| 17 | Probe 2 |
| 18 | Probe 3 |
| 19 | Probe 4 |
| 20 | Probe 5 |
| 21 | Probe 6 |
| 22 | Probe 7 |
| 23 | Probe 8 |
| 24 | Hottest probe |
| 25 | Coldest probe |
| 26 | BMS MOS |
| 27 | BMS board |
| 28 | Heater |
| 29 | Pack |
| 30 | Pack |
| 31 | Pack |
| 32 | Pack |
| 33 | Pack |
| 34 | Pack |
| 35 | Pack |
| 36 | Pack |
| 37 | Pack |
| 38 | Pack |
| 39 | Pack |
| 40 | Pack |
| 41 | Pack |
| 42 | Pack |
| 43 | Pack |
| 44 | Pack |
| 45 | Pack |
| 46 | Pack |
| 47 | Pack |
| 48 | Pack |
| 49 | Pack |
| 50 | Pack |
| 51 | Pack |
| 52 | Pack |
| 53 | Pack |
| 54 | Pack |
| 55 | Pack |
| 56 | Pack |
| 57 | Pack |

## Measurements

| Endpoint | Cluster | Attribute | Measurement | Register |
|---:|---|---|---|---|
| 1 | 0x0b04 | 0x0100 | Pack voltage | 0x0038 |
| 1 | 0x0b04 | 0x0103 | Pack current | 0x0039 |
| 2 | 0x0b04 | 0x0103 | Charge current | 0x0039 |
| 3 | 0x0b04 | 0x0103 | Discharge current | 0x0039 |
| 1 | 0x000c | 0x0055 | State of charge | 0x003a |
| 2 | 0x000c | 0x0055 | Register 003b raw | 0x003b |
| 5 | 0x0b04 | 0x0100 | Cell 1 voltage | 0x0000 |
| 1 | 0x000f | 0x0055 | Cell 1 balancing | 0x004f |
| 6 | 0x0b04 | 0x0100 | Cell 2 voltage | 0x0001 |
| 2 | 0x000f | 0x0055 | Cell 2 balancing | 0x004f |
| 7 | 0x0b04 | 0x0100 | Cell 3 voltage | 0x0002 |
| 3 | 0x000f | 0x0055 | Cell 3 balancing | 0x004f |
| 8 | 0x0b04 | 0x0100 | Cell 4 voltage | 0x0003 |
| 4 | 0x000f | 0x0055 | Cell 4 balancing | 0x004f |
| 9 | 0x0b04 | 0x0100 | Cell 5 voltage | 0x0004 |
| 5 | 0x000f | 0x0055 | Cell 5 balancing | 0x004f |
| 10 | 0x0b04 | 0x0100 | Cell 6 voltage | 0x0005 |
| 6 | 0x000f | 0x0055 | Cell 6 balancing | 0x004f |
| 11 | 0x0b04 | 0x0100 | Cell 7 voltage | 0x0006 |
| 7 | 0x000f | 0x0055 | Cell 7 balancing | 0x004f |
| 12 | 0x0b04 | 0x0100 | Cell 8 voltage | 0x0007 |
| 8 | 0x000f | 0x0055 | Cell 8 balancing | 0x004f |
| 16 | 0x0402 | 0x0000 | Probe 1 temperature | 0x0030 |
| 17 | 0x0402 | 0x0000 | Probe 2 temperature | 0x0031 |
| 18 | 0x0402 | 0x0000 | Probe 3 temperature | 0x0032 |
| 19 | 0x0402 | 0x0000 | Probe 4 temperature | 0x0033 |
| 20 | 0x0402 | 0x0000 | Probe 5 temperature | 0x0034 |
| 21 | 0x0402 | 0x0000 | Probe 6 temperature | 0x0035 |
| 22 | 0x0402 | 0x0000 | Probe 7 temperature | 0x0036 |
| 23 | 0x0402 | 0x0000 | Probe 8 temperature | 0x0037 |
| 3 | 0x000c | 0x0055 | Cell count | 0x003c |
| 4 | 0x000c | 0x0055 | Probe count | 0x003d |
| 5 | 0x000c | 0x0055 | Highest voltage cell | 0x003f |
| 6 | 0x000c | 0x0055 | Lowest voltage cell | 0x0041 |
| 7 | 0x000c | 0x0055 | Hottest probe | 0x0044 |
| 8 | 0x000c | 0x0055 | Coldest probe | 0x0046 |
| 9 | 0x000c | 0x0055 | Temperature spread | 0x0047 |
| 10 | 0x000c | 0x0055 | Remaining Ah | 0x004b |
| 11 | 0x000c | 0x0055 | Charge cycles | 0x004c |
| 12 | 0x000c | 0x0055 | BMS energy | 0x0059 |
| 13 | 0x0b04 | 0x0100 | Highest cell voltage | 0x003e |
| 14 | 0x0b04 | 0x0100 | Lowest cell voltage | 0x0040 |
| 15 | 0x0b04 | 0x0100 | Cell voltage spread | 0x0042 |
| 24 | 0x0402 | 0x0000 | Highest temperature | 0x0043 |
| 25 | 0x0402 | 0x0000 | Lowest temperature | 0x0045 |
| 26 | 0x0402 | 0x0000 | MOS temperature | 0x005a |
| 27 | 0x0402 | 0x0000 | Board temperature | 0x005b |
| 28 | 0x0402 | 0x0000 | Heater temperature | 0x005c |
| 13 | 0x000c | 0x0055 | Operating state (0 idle, 1 charge, 2 discharge) | 0x0048 |
| 4 | 0x0b04 | 0x0103 | Balancing current | 0x004e |
| 9 | 0x000f | 0x0055 | Balancing active | 0x004d |
| 10 | 0x000f | 0x0055 | Charge MOS active | 0x0052 |
| 11 | 0x000f | 0x0055 | Discharge MOS active | 0x0053 |
| 12 | 0x000f | 0x0055 | Precharge MOS active | 0x0054 |
| 13 | 0x000f | 0x0055 | Heater MOS active | 0x0055 |
| 14 | 0x000f | 0x0055 | Fan MOS active | 0x0056 |
| 15 | 0x000f | 0x0055 | Charge MOS command | 0x0121 |
| 16 | 0x000f | 0x0055 | Discharge MOS command | 0x0122 |
| 1 | 0x0b04 | 0x0106 | Pack power | 0x0058 |
| 2 | 0x0b04 | 0x0106 | Charge power | 0x0058 |
| 3 | 0x0b04 | 0x0106 | Discharge power | 0x0058 |
| 14 | 0x000c | 0x0055 | Cell overvoltage alarm level | 0x006d |
| 15 | 0x000c | 0x0055 | Cell undervoltage alarm level | 0x006d |
| 16 | 0x000c | 0x0055 | Cell voltage difference alarm level | 0x006d |
| 17 | 0x000c | 0x0055 | Charge overtemperature alarm level | 0x006d |
| 18 | 0x000c | 0x0055 | Charge undertemperature alarm level | 0x006e |
| 19 | 0x000c | 0x0055 | Discharge overtemperature alarm level | 0x006e |
| 20 | 0x000c | 0x0055 | Discharge undertemperature alarm level | 0x006e |
| 21 | 0x000c | 0x0055 | Temperature difference alarm level | 0x006e |
| 22 | 0x000c | 0x0055 | Pack overvoltage alarm level | 0x006f |
| 23 | 0x000c | 0x0055 | Pack undervoltage alarm level | 0x006f |
| 24 | 0x000c | 0x0055 | Charge overcurrent alarm level | 0x006f |
| 25 | 0x000c | 0x0055 | Discharge overcurrent alarm level | 0x006f |
| 26 | 0x000c | 0x0055 | Low state of charge alarm level | 0x0070 |
| 27 | 0x000c | 0x0055 | Low state of health alarm level | 0x0070 |
| 28 | 0x000c | 0x0055 | MOS overtemperature alarm level | 0x0070 |
| 29 | 0x000c | 0x0055 | Thermal runaway alarm level | 0x0070 |
| 17 | 0x000f | 0x0055 | Smart charger connected | 0x006d |
| 18 | 0x000f | 0x0055 | Smart charger connection fault | 0x006d |
| 19 | 0x000f | 0x0055 | Smart discharger connected | 0x006d |
| 20 | 0x000f | 0x0055 | Smart discharger connection fault | 0x006d |
| 21 | 0x000f | 0x0055 | Charge MOS overtemperature fault | 0x006e |
| 22 | 0x000f | 0x0055 | Charge MOS temperature sensing fault | 0x006e |
| 23 | 0x000f | 0x0055 | Discharge MOS overtemperature fault | 0x006e |
| 24 | 0x000f | 0x0055 | Discharge MOS temperature sensing fault | 0x006e |
| 25 | 0x000f | 0x0055 | Short circuit protection | 0x006f |
| 26 | 0x000f | 0x0055 | Upgrade flag | 0x006f |
| 27 | 0x000f | 0x0055 | Charge undervoltage fault | 0x006f |
| 28 | 0x000f | 0x0055 | Discharge overvoltage fault | 0x006f |
| 29 | 0x000f | 0x0055 | Parallel communication active | 0x0070 |
| 30 | 0x000f | 0x0055 | Parallel communication fault | 0x0070 |
| 31 | 0x000f | 0x0055 | AFE chip fault | 0x0072 |
| 32 | 0x000f | 0x0055 | AFE communication fault | 0x0072 |
| 33 | 0x000f | 0x0055 | AFE sampling fault | 0x0072 |
| 34 | 0x000f | 0x0055 | Cell voltage sensing fault | 0x0072 |
| 35 | 0x000f | 0x0055 | Cell voltage wire disconnected | 0x0072 |
| 36 | 0x000f | 0x0055 | Pack voltage sensing fault | 0x0072 |
| 37 | 0x000f | 0x0055 | Current sensing fault | 0x0072 |
| 38 | 0x000f | 0x0055 | Temperature sensing fault | 0x0072 |
| 39 | 0x000f | 0x0055 | Temperature probe disconnected | 0x0073 |
| 40 | 0x000f | 0x0055 | EEPROM fault | 0x0073 |
| 41 | 0x000f | 0x0055 | Flash fault | 0x0073 |
| 42 | 0x000f | 0x0055 | RTC fault | 0x0073 |
| 43 | 0x000f | 0x0055 | Charge MOS fault | 0x0073 |
| 44 | 0x000f | 0x0055 | Discharge MOS fault | 0x0073 |
| 45 | 0x000f | 0x0055 | Precharge MOS fault | 0x0073 |
| 46 | 0x000f | 0x0055 | Precharge failure | 0x0073 |
| 47 | 0x000f | 0x0055 | Charge MOS disabled by bus | 0x0073 |
| 48 | 0x000f | 0x0055 | Discharge MOS disabled by bus | 0x0073 |
| 49 | 0x000f | 0x0055 | Charge MOS disabled by switch | 0x0073 |
| 50 | 0x000f | 0x0055 | Discharge MOS disabled by switch | 0x0073 |
| 51 | 0x000f | 0x0055 | Fan active | 0x0073 |
| 52 | 0x000f | 0x0055 | Heater active | 0x0073 |
| 53 | 0x000f | 0x0055 | Current limiting active | 0x0073 |
| 54 | 0x000f | 0x0055 | Heater fault | 0x0073 |
| 55 | 0x000f | 0x0055 | BMS warnings | 0x006d |
| 56 | 0x000f | 0x0055 | BMS errors | 0x006d |
| 57 | 0x000f | 0x0055 | BMS communication | 0x0038 |
| 30 | 0x000c | 0x0055 | Remaining mileage raw | 0x005e |
| 31 | 0x000c | 0x0055 | Charging time raw | 0x0064 |
| 32 | 0x000c | 0x0055 | Legacy alarm register 0066 raw | 0x0066 |
| 33 | 0x000c | 0x0055 | Legacy alarm register 0067 raw | 0x0067 |
| 34 | 0x000c | 0x0055 | Legacy alarm register 0068 raw | 0x0068 |
| 35 | 0x000c | 0x0055 | Legacy alarm register 0069 raw | 0x0069 |
| 36 | 0x000c | 0x0055 | Register 0049 raw | 0x0049 |
| 37 | 0x000c | 0x0055 | Register 004a raw | 0x004a |
| 38 | 0x000c | 0x0055 | Register 0050 raw | 0x0050 |
| 39 | 0x000c | 0x0055 | Register 0051 raw | 0x0051 |
| 40 | 0x000c | 0x0055 | Register 0057 raw | 0x0057 |
| 41 | 0x000c | 0x0055 | Register 0071 raw | 0x0071 |
