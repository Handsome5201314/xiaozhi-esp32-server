"""Deterministic, tenant-safe provider routing.

The resolver only handles metadata and selection.  Secret material is supplied
by the server side secret store at call time and is never returned here.
"""
from dataclasses import dataclass
from typing import Iterable, Optional
from urllib.parse import urlparse
import ipaddress
import socket


class ProviderResolutionError(Exception):
    pass


@dataclass(frozen=True)
class ProviderInstance:
    id: str
    tenant_id: str
    user_id: Optional[str]
    device_id: Optional[str]
    capability: str
    base_url: str
    enabled: bool = True
    priority: int = 100
    healthy: bool = True


def validate_provider_url(value: str, allowed_hosts: Iterable[str] = ()) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ProviderResolutionError("Provider 地址必须是 HTTPS URL")
    host = parsed.hostname.rstrip(".").lower()
    allowed = {str(item).lower() for item in allowed_hosts}
    if host in allowed:
        return value
    try:
        address = ipaddress.ip_address(socket.gethostbyname(host))
    except (OSError, ValueError):
        address = None
    if address and (address.is_private or address.is_loopback or address.is_link_local or address.is_reserved):
        raise ProviderResolutionError("Provider 地址不允许访问内网或本机")
    if host in {"localhost", "metadata.google.internal", "instance-data.ec2.internal"}:
        raise ProviderResolutionError("Provider 地址不允许访问本机或云元数据")
    return value


class ProviderResolver:
    def __init__(self, instances: Iterable[ProviderInstance] = (), allowed_hosts: Iterable[str] = ()):
        self._instances = list(instances)
        self.allowed_hosts = tuple(allowed_hosts)

    def resolve(self, tenant_id: str, user_id: str, device_id: str, capability: str) -> ProviderInstance:
        candidates = []
        for instance in self._instances:
            if not instance.enabled or not instance.healthy or instance.tenant_id != tenant_id or instance.capability != capability:
                continue
            if instance.user_id not in (None, user_id) or instance.device_id not in (None, device_id):
                continue
            validate_provider_url(instance.base_url, self.allowed_hosts)
            # device > user > tenant; lower priority wins within a tier
            specificity = 0 if instance.device_id == device_id else 1 if instance.user_id == user_id else 2
            candidates.append((specificity, instance.priority, instance.id, instance))
        if not candidates:
            raise ProviderResolutionError(f"没有可用的 {capability} Provider")
        return min(candidates, key=lambda item: item[:3])[-1]
