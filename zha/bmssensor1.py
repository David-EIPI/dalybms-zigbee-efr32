"""Use endpoint Basic.ProductLabel as the subject of otherwise generic names.

Requires the ZHA device-class API in zha/zha-quirks 2.2.2. Add manufacturer/model
pairs to SUPPORTED_MODELS to reuse the same naming convention on other devices.
"""

from zhaquirks.builder import QuirkBuilder
from zhaquirks.builder.device import QuirkV2Device
from zigpy.zcl.clusters.general import Basic

from zha.application.helpers import safe_read
from zha.application.platforms import PlatformEntity


SUPPORTED_MODELS = (("DS", "bmssensor1"),)

# Quantity aliases, independent of manufacturer, model and endpoint numbering.
QUANTITY_NAMES = {
    "dc_voltage": "voltage",
    "dc_current": "current",
    "dc_power": "power",
}


def endpoint_label(entity: PlatformEntity) -> str | None:
    """Return a usable label without interfering with description-based names."""
    cluster = entity._cluster
    if cluster.cluster_id == Basic.cluster_id:
        return None
    # BACnet-style clusters own their labels, including when not yet cached.
    if "description" in cluster.attributes_by_name:
        return None
    basic = cluster.endpoint.in_clusters.get(Basic.cluster_id)
    if basic is None:
        return None
    label = basic.get(Basic.AttributeDefs.product_label.name)
    if not isinstance(label, str) or not label.strip():
        return None
    return label.strip()


def apply_product_label(entity: PlatformEntity) -> None:
    """Change only display metadata; keep default entities and their unique IDs."""
    label = endpoint_label(entity)
    if label is None:
        return
    # Remember the unmodified quantity across rediscovery/capability updates.
    quantity = getattr(entity, "_product_label_quantity", None)
    if quantity is None:
        quantity = (
            entity.fallback_name
            or entity.translation_key
            or entity.device_class
            or getattr(entity, "_attribute_name", None)
            or entity._cluster.ep_attribute
        )
        quantity = QUANTITY_NAMES.get(quantity, quantity).replace("_", " ")
        entity._product_label_quantity = quantity
    entity._attr_fallback_name = f"{label} {quantity}"
    # A custom untranslated key makes HA prefer our fallback over DC/device-class
    # translations. It is display metadata, not part of the entity's unique ID.
    entity._attr_translation_key = "endpoint_product_label"
    entity._attr_primary = False


class ProductLabelDevice(QuirkV2Device):
    """Read endpoint labels before ZHA discovers and publishes entity names."""

    async def async_initialize(self, from_cache: bool = False) -> None:
        for endpoint_id, endpoint in self._zigpy_device.endpoints.items():
            if endpoint_id == 0:
                continue
            basic = endpoint.in_clusters.get(Basic.cluster_id)
            if basic is not None:
                # Cached startup uses persisted labels; cache misses still read
                # the device. Failure leaves the default name or last good label.
                await safe_read(
                    basic,
                    [Basic.AttributeDefs.product_label.name],
                    allow_cache=from_cache,
                )
        await super().async_initialize(from_cache)

    def _apply_entity_metadata_changes(self, entity: PlatformEntity) -> None:
        super()._apply_entity_metadata_changes(entity)
        if isinstance(entity, PlatformEntity):
            apply_product_label(entity)

    def _add_entity(self, entity: PlatformEntity, *, emit_event: bool = True) -> None:
        # Capability recomputation runs between discovery and publication.
        if isinstance(entity, PlatformEntity):
            apply_product_label(entity)
        super()._add_entity(entity, emit_event=emit_event)


builder = QuirkBuilder(*SUPPORTED_MODELS[0]).zha_device_class(ProductLabelDevice)
for manufacturer, model in SUPPORTED_MODELS[1:]:
    builder.applies_to(manufacturer, model)
builder.add_to_registry()
