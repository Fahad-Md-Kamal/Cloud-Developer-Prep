"""
Testing Strategies for Distributed Resilience Patterns
------------------------------------------------------

Uses pytest-style tests to validate circuit breaker transitions,
load-balancing fairness, and eventual consistency projections.
"""

from __future__ import annotations

import time

import pytest

from fault_tolerance import CircuitBreaker, CircuitOpenError
from load_balancing import Backend, WeightedRoundRobin
from consistency_strategies import Event, EventLog, ReadModel
from scaling_strategies import ShardingManager


def test_circuit_breaker_opens_and_recovers() -> None:
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

    def failing() -> None:
        raise ValueError("boom")

    with pytest.raises(ValueError):
        breaker.call(failing)
    with pytest.raises(ValueError):
        breaker.call(failing)

    with pytest.raises(CircuitOpenError):
        breaker.call(lambda: None)

    time.sleep(0.15)
    breaker.call(lambda: "ok")  # closes after successful call


def test_weighted_round_robin_distribution() -> None:
    backends = [Backend("a", "eu", weight=2), Backend("b", "us", weight=1)]
    balancer = WeightedRoundRobin(backends)
    selections = [balancer.select().name for _ in range(6)]
    assert selections.count("a") > selections.count("b")


def test_eventual_consistency_projection() -> None:
    log = EventLog()
    read_model = ReadModel()
    event = Event("doc-1", "CLASSIFIED", {"label": "Contract"})
    log.append(event)
    for e in log.replay():
        read_model.apply(e)
    assert read_model.get("doc-1")["CLASSIFIED"]["label"] == "Contract"


def test_sharding_spreads_tenants() -> None:
    sharder = ShardingManager(shard_count=8)
    tenants = {"law-eu", "law-us", "opt-enterprise", "opt-beta"}
    shards = {sharder.shard_for(tenant) for tenant in tenants}
    assert len(shards) >= 2
