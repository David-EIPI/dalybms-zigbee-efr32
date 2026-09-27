# Endpoint ProductLabel naming for ZHA

[bmssensor1.py](bmssensor1.py) is a reusable naming quirk. It reads Basic
`ProductLabel` (`0x000e`) on each endpoint and combines that subject with the
entity's quantity. There is no BMS endpoint-to-name table.

| Endpoint ProductLabel | Measurement | Entity name |
|---|---|---|
| Pack | DC voltage | Pack voltage |
| Pack | DC current | Pack current |
| Cell 1 | DC voltage | Cell 1 voltage |
| Balancer | DC current | Balancer current |
| Probe 1 | Temperature | Probe 1 temperature |

Home Assistant may also prefix the entity name with the device name.

## Behavior

- Uses the Basic cluster on the **same endpoint** as the entity's backing cluster.
  It never borrows endpoint 1's label for other endpoints.
- Leaves description-bearing clusters, including Analog Input and Binary Input,
  to ZHA's existing description handling. This also applies when their description
  has not yet been cached.
- Applies to endpoint-backed entities in other clusters. Device-wide diagnostics
  without a backing cluster and entities backed by Basic are unaffected.
- Derives the quantity from the existing fallback name, translation key, device
  class, measurement attribute, or cluster name, in that order. Underscores become
  spaces; `dc_voltage`, `dc_current`, and `dc_power` become `voltage`, `current`,
  and `power`. Other modifiers, such as phases, remain in the name.
- Uses an untranslated custom key so HA uses the composed English fallback name
  instead of its generic translated name. These names are not localized.
- Reads labels before normal ZHA initialization/discovery. On cached startup it
  uses persisted labels, reading the device if the cache is empty. On normal
  initialization it requests fresh labels. Reads are sequential and do not add
  reporting configurations or bindings.
- Missing Basic, unsupported/empty/whitespace labels and failed reads leave the
  default names in place. A previously cached usable label survives a read failure.
- Renames existing entities in place. Unique IDs, entity classes, measurements,
  scaling, units and reporting remain unchanged. No duplicates or obsolete
  original entities are created.

`ProductLabel` is one subject per endpoint. Every eligible entity on that endpoint
uses the same subject. If unrelated electrical and temperature readings share an
endpoint, firmware must choose a label meaningful for both or allocate separate
endpoints. Cluster descriptions remain independent of ProductLabel.

Labels are initialization metadata, not continuously monitored state. Restart HA
when changing firmware labels; cached startups can reuse old labels, so use ZHA's
re-interview/reconfigure facility to refresh the device, then restart if necessary.
Manual entity-name overrides in HA continue to take precedence.

## Install and reuse

Requires the runtime device-class API in **ZHA 2.2.2 / zha-quirks 2.2.2**, as pinned
by the supplied HA source. Older releases with only `zigpy.quirks.v2` are not
supported by this version. The quirk uses internal naming/lifecycle hooks; future
ZHA changes may require adaptation.

1. Copy **only** `bmssensor1.py` into `/config/custom_zha_quirks/` on Home Assistant
   (or your existing custom quirk directory). Replace the earlier fixed-name file;
   keep only one custom quirk targeting each manufacturer/model.
2. Merge this into `configuration.yaml`, without adding a second `zha:` section:

   ```yaml
   zha:
     enable_quirks: true
     custom_quirks_path: /config/custom_zha_quirks
   ```

3. Restart Home Assistant. Check the device's entity names and ZHA diagnostics.
   Inspect logs for custom quirk import errors if it does not apply.
4. Clear any manually assigned entity-name override to use the new default name.

To apply the same convention to another device, add its exact Basic manufacturer
and model strings to the file's `SUPPORTED_MODELS` tuple, for example:

```python
SUPPORTED_MODELS = (
    ("DS", "bmssensor1"),
    ("DS", "another_sensor"),
)
```

The naming logic requires no changes for different endpoint numbers or quantities.
Matching is explicit to avoid taking over unrelated devices or their other quirks.
Devices that need a separate functional quirk require integrating this naming
behavior into that quirk; ZHA does not stack multiple matching quirks.

The application must expose Basic ProductLabel with its intended value on every
endpoint that needs a subject. This change uses the application's populated labels;
it does not modify or flash firmware.

Existing `entity_id` strings (such as `sensor.bms_dc_voltage_2`) are preserved by
HA's entity registry, even when display names change. This preserves automation
references and history. Rename IDs separately in HA if desired, reviewing explicit
YAML references. Do not delete the original entities or remove/re-pair the device.
Remove the file and restart HA to return to default naming.

## Why this needs a quirk

Stock ZHA's Electrical Measurement entities use fixed `dc_voltage`, `dc_current`
and `dc_power` translation keys. Neither ZHA nor HA uses Basic ProductLabel for
these names. The attribute exists in zigpy, so firmware and this quirk can agree
on its use as an endpoint subject without custom cluster definitions.

Relevant upstream sources:

- [zigpy Basic attributes](https://github.com/zigpy/zigpy/blob/dev/zigpy/zcl/clusters/general.py):
  `Basic.AttributeDefs.product_label`.
- [ZHA entity types](https://github.com/zigpy/zha/blob/dev/zha/application/platforms/sensor/__init__.py):
  Electrical Measurement, Temperature and Analog Input naming/scaling.
- [ZHA device lifecycle](https://github.com/zigpy/zha/blob/dev/zha/zigbee/device.py):
  discovery, initialization and entity publication.
- [HA name resolution](https://github.com/home-assistant/core/blob/dev/homeassistant/components/zha/entity.py):
  fallback/translation precedence.

Source revisions inspected: HA `11a2f455d25`, ZHA `c556ae20`, zigpy `512f3cf`.

## Validation

Eight integration cases pass using ZHA's simulated gateway: the full documented
57-endpoint BMS layout with/without the quirk, nonmatching-model isolation,
preservation of 98 description-based names, 19 electrical readings and 13
temperatures, stable entity identities/classes/values, and reuse on another model
at endpoint 42. Label cases include cached, initially uncached, blank, unsupported,
timeout and missing Basic. Rediscovery does not duplicate the label prefix.

This is local software validation. Installation on the running HA instance and
real-device reads remain to be verified there.

The integration tests use ZHA's simulated gateway fixtures. From the repository
root, with Python 3.14:

```sh
git clone https://github.com/zigpy/zha.git /tmp/bms-zha-source
git -C /tmp/bms-zha-source checkout c556ae20
python3 -m venv /tmp/bms-zha-venv
/tmp/bms-zha-venv/bin/python -m pip install \
  -e /tmp/bms-zha-source 'zha-quirks==2.2.2' pytest \
  'pytest-asyncio==0.26.0' looptime pytest-timeout
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/tmp/bms-zha-source \
  /tmp/bms-zha-venv/bin/python -m pytest \
  -p tests.conftest -o asyncio_mode=auto \
  -o asyncio_default_fixture_loop_scope=function \
  tests/test_zha_names.py -q --show-capture=no --disable-warnings
```

The tests require no radio or BMS.
