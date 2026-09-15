"""User/device scoped Hermes failover."""
from dataclasses import dataclass
from typing import Iterable, Optional

from .provider_resolver import ProviderResolutionError, validate_provider_url


@dataclass(frozen=True)
class HermesInstance:
    id: str
    tenant_id: str
    user_id: str
    device_id: Optional[str]
    base_url: str
    capabilities: frozenset[str]
    priority: int = 100
    enabled: bool = True
    healthy: bool = True


class HermesResolver:
    def __init__(self, instances: Iterable[HermesInstance] = (), allowed_hosts: Iterable[str] = ()):
        self.instances = list(instances)
        self.allowed_hosts = tuple(allowed_hosts)

    def resolve(self, tenant_id: str, user_id: str, device_id: str, capability: str = "chat") -> HermesInstance:
        candidates = []
        for instance in self.instances:
            if (instance.tenant_id != tenant_id or instance.user_id != user_id or
                    instance.device_id not in (None, device_id) or not instance.enabled or
                    not instance.healthy or capability not in instance.capabilities):
                continue
            validate_provider_url(instance.base_url, self.allowed_hosts)
            specificity = 0 if instance.device_id == device_id else 1
            candidates.append((specificity, instance.priority, instance.id, instance))
        if not candidates:
            raise ProviderResolutionError("当前用户没有可用的 Hermes 实例")
        return min(candidates, key=lambda item: item[:3])[-1]
