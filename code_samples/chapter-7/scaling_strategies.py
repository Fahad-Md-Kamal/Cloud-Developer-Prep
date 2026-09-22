"""
Scaling, Sharding, and Load Leveling Strategies
-----------------------------------------------

Provides helper classes for capacity planning, sharding, caching, and queue
based load leveling that senior engineers rely on during system design.
"""

from __future__ import annotations

import asyncio
import logging
import math
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Callable

import yaml


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
CONFIG_PATH = Path(__file__).resolve().parent / "resilience-config.yaml"


@dataclass(frozen=True)
class CapacityPlan:
    desired_nodes: int
    per_node_rps: int
    headroom_percentage: float


class CapacityPlanner:
    """Estimate compute footprint given latency and traffic targets."""

    def __init__(self, per_node_rps: int = 500, headroom_percentage: float = 0.3) -> None:
        self.per_node_rps = per_node_rps
        self.headroom_percentage = headroom_percentage

    def plan(self, expected_rps: int) -> CapacityPlan:
        raw_nodes = expected_rps / self.per_node_rps
        desired = math.ceil(raw_nodes * (1 + self.headroom_percentage))
        return CapacityPlan(desired_nodes=max(1, desired), per_node_rps=self.per_node_rps, headroom_percentage=self.headroom_percentage)


class ShardingManager:
    """Assign tenants or datasets to shards with consistent hashing."""

    def __init__(self, shard_count: int) -> None:
        self.shard_count = shard_count

    def shard_for(self, tenant_id: str) -> int:
        return hash(tenant_id) % self.shard_count


class CacheOrchestrator:
    """Manage multi-layer caches with TTL boundaries."""

    def __init__(self, ttl_seconds: int = 60) -> None:
        self.ttl_seconds = ttl_seconds
        self._store: Dict[str, tuple[float, Any]] = {}

    def get(self, key: str, loader: Callable[[], Any]) -> Any:
        now = time.time()
        value = self._store.get(key)
        if value and value[0] > now:
            return value[1]
        fresh = loader()
        self._store[key] = (now + self.ttl_seconds, fresh)
        return fresh


class QueueLoadLeveler:
    """Throttle bursts via an async queue with worker pools."""

    def __init__(self, workers: int = 3) -> None:
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.workers = workers

    async def enqueue(self, item: str) -> None:
        await self.queue.put(item)

    async def worker(self, name: str) -> None:
        while True:
            item = await self.queue.get()
            await asyncio.sleep(random.uniform(0.05, 0.2))
            logging.info("%s processed %s", name, item)
            self.queue.task_done()

    async def start(self) -> None:
        tasks = [asyncio.create_task(self.worker(f"worker-{i}")) for i in range(self.workers)]
        await self.queue.join()
        for task in tasks:
            task.cancel()


def load_resilience_config() -> Dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as fp:
        return yaml.safe_load(fp)


async def simulate_queue_leveling() -> None:
    leveler = QueueLoadLeveler(workers=2)
    producer = asyncio.create_task(
        asyncio.gather(*(leveler.enqueue(f"legal-doc-{i}") for i in range(5)))
    )
    consumer = asyncio.create_task(leveler.start())
    await producer
    await consumer


def demo() -> None:
    planner = CapacityPlanner(per_node_rps=800, headroom_percentage=0.25)
    plan = planner.plan(expected_rps=4200)
    logging.info("capacity plan -> %s nodes", plan.desired_nodes)

    sharder = ShardingManager(shard_count=12)
    tenant = "lawstronaut-enterprise"
    logging.info("tenant %s assigned shard %s", tenant, sharder.shard_for(tenant))

    cache = CacheOrchestrator(ttl_seconds=2)
    data = cache.get("optimizely:feature", loader=lambda: {"rollout": random.randint(1, 100)})
    logging.info("cache read %s", data)

    cfg = load_resilience_config()
    logging.info("loaded config keys: %s", list(cfg.keys()))


if __name__ == "__main__":
    demo()
    asyncio.run(simulate_queue_leveling())
