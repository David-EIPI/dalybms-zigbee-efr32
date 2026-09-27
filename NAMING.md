# Firmware naming attributes

Every endpoint exposes the standard Basic cluster (0x0000) with a read-only,
non-singleton ProductLabel attribute (0x000e, ZCL character string). Labels identify
the source of Electrical Measurement and Temperature Measurement values. The
cluster/attribute identifies the measurement type. Basic cluster revision is 3.
Manufacturer DS and model bmssensor1 remain on endpoint 1.

| Endpoint | ProductLabel |
|---|---|
| 1 | Pack |
| 2 | Pack charge |
| 3 | Pack discharge |
| 4 | Balancer |
| 5–12 | Cell 1 through Cell 8 |
| 13 | Highest cell |
| 14 | Lowest cell |
| 15 | Cell spread |
| 16–23 | Probe 1 through Probe 8 |
| 24 | Hottest probe |
| 25 | Coldest probe |
| 26 | BMS MOS |
| 27 | BMS board |
| 28 | Heater |
| 29–57 | Pack |

Analog Input (0x000c) and Binary Input (0x000f) carry their own field names in
Description (0x001c). Their entity names should use Description independently of
ProductLabel: for example, endpoint 1 contains Pack electrical measurements and
the separately described `Cell 1 balancing` Binary Input. All 41 Analog Input
and 57 Binary Input descriptions are nonempty and unique within their cluster
type. Deliberate abbreviations replace truncated words in Binary Input names.
There are no output clusters: this application is read-only.

Electrical, Analog Input and Binary Input endpoint numbers are unchanged.
Temperature clusters move from endpoints 1–13 to 16–28 so they have distinct
source labels. Different cluster types may share endpoints; multiple independent
instances of the same cluster require separate endpoints. See [ENDPOINTS.md](ENDPOINTS.md)
for every field. The optional [ZHA quirk](zha/README.md) consumes these labels
when composing Home Assistant entity names.

Fixed ProductLabel strings use their actual encoded length in attribute RAM,
instead of reserving the maximum 64-byte payload on every endpoint. The standard
ZCL character-string encoding is retained. This build has 1041 attributes, 183
cluster instances (57 Basic plus 126 measurement clusters), and 4935 attribute
RAM bytes. Flash usage is 184516 bytes text plus 972 initialized data; BSS is
27404 bytes. The 4 KiB stack and minimum 2 KiB heap reservations still fit.

## Upgrade and validation

The temperature address change and newly advertised Basic clusters require a
fresh Home Assistant interview. Remove/re-add the device, or use an interview
mechanism that refreshes active endpoints and simple descriptors; merely using
cached descriptors will not discover the new temperature clusters.

On the first boot of this endpoint-layout version, the firmware clears obsolete
bindings and reporting entries while preserving network credentials. Default
reporting entries are then loaded, but coordinator bindings/configuration must
be recreated by Home Assistant before automatic reports resume. Later boots
preserve that configuration. The migration marker uses application NVM3 user-domain
key 0x0b501 with layout value 0x424d5302; no stack keys or credentials are erased.

Build and host protocol/metric checks passed. Generated checks cover all labels,
Description lengths/uniqueness, unchanged general-input endpoint assignments,
and binding-table capacity. Flash verification and live RAM validation passed:
715 static labels/scales/constants checked and 130 measurement values decoded.
After the restart, 32/32 BMS reads succeeded and 22 reports were APS-acknowledged
with no delivery failures. Coordinator reconfiguration was underway (38 binding
destinations, 162 reporting entries). Complete Home Assistant discovery of the
new clusters and the label-consuming quirk update remain follow-up steps.
