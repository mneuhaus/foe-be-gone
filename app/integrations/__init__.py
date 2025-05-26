"""Integration modules for Foe Be Gone."""
from .dummy_surveillance import DummySurveillanceIntegration
from .unifi_protect import UniFiProtectIntegration

# Registry of available integrations
INTEGRATIONS = {
    "dummy_surveillance": DummySurveillanceIntegration,
    "unifi_protect": UniFiProtectIntegration
}

def get_integration_class(integration_type: str):
    """Get integration class by type."""
    return INTEGRATIONS.get(integration_type)