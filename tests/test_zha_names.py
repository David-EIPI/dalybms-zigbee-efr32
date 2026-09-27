"""Exercise ProductLabel naming with the reference ZHA simulated gateway.

See zha/README.md for the test command and dependencies.
"""

from pathlib import Path
import runpy
from unittest.mock import AsyncMock

import pytest
from zigpy.const import SIG_EP_INPUT, SIG_EP_OUTPUT, SIG_EP_PROFILE, SIG_EP_TYPE
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

from tests.common import create_mock_zigpy_device, join_zigpy_device
from zha.application import Platform
from zha.quirks import DeviceRegistry
from zha.zigbee.device import Device

BMS = Path(__file__).resolve().parents[1]


def endpoint_map():
    """Build the device independently of the quirk, from the firmware map."""
    endpoints, attributes, electrical = {}, {}, {}
    for line in (BMS / "ENDPOINTS.md").read_text().splitlines():
        fields = [s.strip() for s in line.split("|")[1:-1]]
        if len(fields) != 5 or not fields[1].startswith("0x"):
            continue
        ep, cluster, attr, name, _reg = fields
        ep, cluster, attr = int(ep), int(cluster, 16), int(attr, 16)
        spec = endpoints.setdefault(ep, {
            SIG_EP_INPUT: [Basic.cluster_id], SIG_EP_OUTPUT: [],
            SIG_EP_PROFILE: 0x0104, SIG_EP_TYPE: 0x000C,
        })
        if cluster not in spec[SIG_EP_INPUT]:
            spec[SIG_EP_INPUT].append(cluster)
        values = attributes.setdefault(ep, {})
        if cluster == ElectricalMeasurement.cluster_id:
            attribute = ElectricalMeasurement.attributes[attr].name
            divisor = 1000 if ep >= 4 else 10
            if attribute == "dc_power":
                divisor = 1
            raw = -125 if attribute == "dc_current" else 3210
            values.setdefault("electrical_measurement", {}).update({
                attribute: raw, f"{attribute}_multiplier": 1,
                f"{attribute}_divisor": divisor,
            })
            electrical[ep, attribute] = raw / divisor
        elif cluster == 0x0402:
            values["temperature"] = {"measured_value": 2345}
        elif cluster == 0x000C:
            values["analog_input"] = {
                "present_value": 12.0, "description": name, "engineering_units": 95,
            }
        elif cluster == 0x000F:
            values["binary_input"] = {"present_value": 1, "description": name}
    return endpoints, attributes, electrical


def plug_measurements(device, attributes):
    for ep, clusters in attributes.items():
        for cluster_name, values in clusters.items():
            cluster = getattr(device.endpoints[ep], cluster_name)
            cluster.PLUGGED_ATTR_READS = values
            if cluster.cluster_id == ElectricalMeasurement.cluster_id:
                for attr in ElectricalMeasurement.attributes.values():
                    if attr.name not in values:
                        cluster.add_unsupported_attribute(attr.name)


@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["bmssensor1", "another_model"])
async def test_names_keep_identity_and_measurements(zha_gateway, model):
    runpy.run_path(str(BMS / "zha" / "bmssensor1.py"))
    endpoints, attributes, expected = endpoint_map()
    snapshots = []
    for index, use_quirk in enumerate((False, True)):
        kwargs = {} if use_quirk else {"registry": DeviceRegistry()}
        device = create_mock_zigpy_device(
            zha_gateway, endpoints, manufacturer="DS", model=model,
            ieee=f"00:0d:6f:00:0a:90:69:{index:02x}",
            attributes=attributes, **kwargs,
        )
        plug_measurements(device, attributes)
        for ep in endpoints:
            basic = device.endpoints[ep].basic
            # No cached label: the quirk must actually read it before discovery.
            assert basic.get("product_label") is None
            basic.PLUGGED_ATTR_READS = {"product_label": f"Channel {ep}"}
        zha_device = await join_zigpy_device(zha_gateway, device)
        snapshot, found = {}, {}
        temperature_count = description_count = 0
        renamed = use_quirk and model == "bmssensor1"
        for entity in zha_device.platform_entities.values():
            identity = entity.unique_id.removeprefix(str(device.ieee))
            snapshot[identity] = (type(entity), getattr(entity, "native_value", None))
            cluster = getattr(entity, "_cluster", None)
            if cluster is None:
                continue
            if "description" in cluster.attributes_by_name:
                assert entity.fallback_name == cluster.get("description")
                description_count += 1
            if cluster.cluster_id == 0x0402:
                assert entity.native_value == 23.45
                if renamed:
                    assert entity.fallback_name == f"Channel {entity.endpoint.id} temperature"
                temperature_count += 1
            if entity.PLATFORM != Platform.SENSOR:
                continue
            key = (entity.endpoint.id, getattr(entity, "_attribute_name", None))
            if key not in expected:
                continue
            assert key not in found, "Duplicate electrical sensor"
            found[key] = entity
            assert entity.native_value == pytest.approx(expected[key])
            if renamed:
                assert entity.fallback_name == f"Channel {key[0]} {key[1].removeprefix('dc_')}"
                assert entity.state.fallback_name == entity.fallback_name
                assert entity.translation_key == "endpoint_product_label"
                assert not entity.primary
            else:
                assert entity.fallback_name is None
                assert entity.translation_key == key[1]
        assert len(found) == 19
        assert found.keys() == expected.keys()
        assert temperature_count == 13
        assert description_count == 98
        snapshots.append(snapshot)
        await zha_device.recompute_entities()
        for entity in found.values():
            if renamed:
                assert entity.fallback_name.count("Channel") == 1
    assert snapshots[0] == snapshots[1]


@pytest.mark.asyncio
@pytest.mark.parametrize("label_source", ["cache", "read", "empty", "unsupported", "timeout", "no_basic"])
async def test_cached_startup_and_missing_labels(zha_gateway, label_source):
    quirk = runpy.run_path(str(BMS / "zha" / "bmssensor1.py"))
    # Reuse the same class for a different manufacturer/model and arbitrary endpoint.
    registry = DeviceRegistry()
    (quirk["QuirkBuilder"]("Example", "sensor2", registry=registry)
     .zha_device_class(quirk["ProductLabelDevice"]).add_to_registry())
    clusters = [0x0402] if label_source == "no_basic" else [0x0000, 0x0402]
    device = create_mock_zigpy_device(
        zha_gateway,
        {42: {SIG_EP_INPUT: clusters, SIG_EP_OUTPUT: [],
              SIG_EP_PROFILE: 0x0104, SIG_EP_TYPE: 0x000C}},
        manufacturer="Example", model="sensor2", registry=registry,
        attributes={42: {"temperature": {"measured_value": 2100}}},
    )
    basic = device.endpoints[42].in_clusters.get(Basic.cluster_id)
    if label_source == "cache":
        basic.update_attribute(Basic.AttributeDefs.product_label.id, " Auxiliary ")
    elif label_source == "read":
        basic.PLUGGED_ATTR_READS = {"product_label": "Auxiliary"}
    elif label_source == "empty":
        basic.PLUGGED_ATTR_READS = {"product_label": "   "}
    elif label_source == "timeout":
        basic.read_attributes = AsyncMock(side_effect=TimeoutError)
    elif label_source == "unsupported":
        basic.add_unsupported_attribute("product_label")
    zha_device = Device.new(device, zha_gateway)
    zha_gateway._devices[device.ieee] = zha_device
    await zha_device.async_initialize(from_cache=True)
    entities = [e for e in zha_device.platform_entities.values()
                if getattr(e, "_attribute_name", None) == "measured_value"]
    assert len(entities) == 1
    entity = entities[0]
    assert entity.native_value == 21
    if label_source in ("cache", "read"):
        assert entity.fallback_name == "Auxiliary temperature"
        assert entity.translation_key == "endpoint_product_label"
    else:
        assert entity.fallback_name is None
        assert entity.translation_key is None
    if label_source == "cache":
        basic.read_attributes_raw.assert_not_called()
    elif label_source == "read":
        basic.read_attributes_raw.assert_called_once()
