"""
Load Balancing Strategies for Global Traffic
-------------------------------------------

Implements weighted round-robin, least-connections, and geo-aware routing
used by Lawstronaut's crawler fleet and Optimizely's personalization APIs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Iterable, List, Sequence


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


@dataclass
class Backend:
    """Represents a service replica that can receive traffic."""

    name: str
    region: str
    weight: int = 1
    latency_ms: float = 20.0
    active_connections: int = field(default=0, init=False)


class WeightedRoundRobin:
    """Simple weighted round-robin balancer."""

    def __init__(self, backends: Sequence[Backend]) -> None:
        self._expanded: List[Backend] = [
            backend for backend in backends for _ in range(max(1, backend.weight))
        ]
        self._index = 0

    def select(self) -> Backend:
        backend = self._expanded[self._index]
        self._index = (self._index + 1) % len(self._expanded)
        backend.active_connections += 1
        return backend

    @staticmethod
    def release(backend: Backend) -> None:
        backend.active_connections = max(0, backend.active_connections - 1)


class LeastConnectionsBalancer:
    """Assign requests to the backend with the fewest active connections."""

    def __init__(self, backends: Sequence[Backend]) -> None:
        self.backends = list(backends)

    def select(self) -> Backend:
        backend = min(self.backends, key=lambda b: (b.active_connections, b.latency_ms))
        backend.active_connections += 1
        return backend


class GeoRouter:
    """Route clients to the closest healthy region, fall back to fastest replica."""

    def __init__(self, backends: Sequence[Backend]) -> None:
        self.backends = list(backends)

    def route(self, client_region: str) -> Backend:
        regional = [backend for backend in self.backends if backend.region == client_region]
        candidates = regional or self.backends
        backend = min(candidates, key=lambda b: b.latency_ms)
        backend.active_connections += 1
        return backend


class TrafficScaler:
    """Translate latency/error metrics into scaling recommendations."""

    def __init__(self, min_instances: int = 2, max_instances: int = 20) -> None:
        self.min_instances = min_instances
        self.max_instances = max_instances

    def recommend(self, p95_latency_ms: float, error_rate: float) -> int:
        baseline = max(self.min_instances, int(p95_latency_ms / 40))
        penalty = int(error_rate * 10)
        desired = baseline + penalty
        return max(self.min_instances, min(self.max_instances, desired))


def simulate_global_routing() -> None:
    """Show how routing and scaling work together."""
    pools = [
        Backend(name="law-eu-1", region="eu", weight=3, latency_ms=18),
        Backend(name="law-us-1", region="us", weight=2, latency_ms=32),
        Backend(name="opt-apac-1", region="apac", weight=1, latency_ms=55),
    ]

    geo_router = GeoRouter(pools)
    scaler = TrafficScaler(min_instances=3, max_instances=10)

    for region in ("eu", "us", "latam", "apac"):
        backend = geo_router.route(region)
        logging.info("region %s handled by %s (latency=%sms)", region, backend.name, backend.latency_ms)
        WeightedRoundRobin.release(backend)

    recommendation = scaler.recommend(p95_latency_ms=180, error_rate=0.07)
    logging.info("scale to %s pods based on metrics", recommendation)


if __name__ == "__main__":
    simulate_global_routing()
