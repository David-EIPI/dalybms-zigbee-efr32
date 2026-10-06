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
Analog Value (0x000e) on endpoint 1 uses Description **Update interval** and
EngineeringUnits **seconds**. Its PresentValue (0x0055) configures the sampling
cadence and is the only remotely writable attribute. All BMS data remain
read-only. See [CONFIGURATION.md](CONFIGURATION.md#runtime-update-interval).

Electrical, Analog Input and Binary Input endpoint numbers are unchanged.
Temperature clusters move from endpoints 1–13 to 16–28 so they have distinct
source labels. Different cluster types may share endpoints; multiple independent
instances of the same cluster require separate endpoints. See [ENDPOINTS.md](ENDPOINTS.md)
for every field. The optional [ZHA quirk](zha/README.md) consumes these labels
when composing Home Assistant entity names.

Fixed ProductLabel strings use their actual encoded length in attribute RAM,
instead of reserving the maximum 64-byte payload on every endpoint. The standard
ZCL character-string encoding is retained. This build has 1049 attributes, 184
cluster instances (57 Basic, 126 measurement clusters and one Analog Value),
and 4999 attribute RAM bytes. The 4 KiB stack and minimum 2 KiB heap
reservations still fit.

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
key 0x0b501 with layout value 0x424d5303; no stack keys or credentials are erased.
The new Analog Value cluster likewise requires descriptor rediscovery after
an upgrade. The persisted interval uses its own key, 0x0b502.

Build and host protocol/metric/settings checks passed. Generated checks cover all labels,
Description lengths/uniqueness, unchanged general-input endpoint assignments,
binding-table capacity and the sole writable Analog Value attribute.
The following live results are from the earlier PA1/PA0 firmware validation;
the PD10/PD12 wiring and runtime setting still require live verification.
Flash verification and live RAM validation passed:
715 static labels/scales/constants checked and 130 measurement values decoded.
After the restart, 32/32 BMS reads succeeded and 22 reports were APS-acknowledged
with no delivery failures. Coordinator reconfiguration was underway (38 binding
destinations, 162 reporting entries). Complete Home Assistant discovery of the
new clusters and the label-consuming quirk update remain follow-up steps.
