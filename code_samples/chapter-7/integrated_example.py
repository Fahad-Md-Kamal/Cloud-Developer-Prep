"""
Integrated Example: Global Feature Delivery Platform
----------------------------------------------------

Demonstrates how fault tolerance, load balancing, and scaling utilities
work together for a Lawstronaut/Optimizely inspired system.
"""

from __future__ import annotations

import random
import sys
import time
from pathlib import Path
from typing import Dict


CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.append(str(CURRENT_DIR))

from fault_tolerance import CircuitBreaker, CircuitOpenError, graceful_degradation, retry_with_backoff
from load_balancing import Backend, WeightedRoundRobin
from scaling_strategies import CapacityPlanner, load_resilience_config


def call_optimizely_model() -> str:
    if random.random() < 0.3:
        raise TimeoutError("LLM inference timeout")
    return "personalized legal insight"


def route_request(balancer: WeightedRoundRobin) -> Backend:
    backend = balancer.select()
    time.sleep(random.uniform(0.01, 0.03))
    WeightedRoundRobin.release(backend)
    return backend


def main() -> None:
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=3, name="ai-model")
    balancer = WeightedRoundRobin(
        [
            Backend(name="edge-eu", region="eu", weight=3, latency_ms=22),
            Backend(name="edge-us", region="us", weight=2, latency_ms=28),
        ]
    )
    planner = CapacityPlanner(per_node_rps=600, headroom_percentage=0.3)
    config: Dict[str, Dict[str, Dict[str, int]]] = load_resilience_config()

    rollout_target = config["optimizely"]["autoscaling"]["target_rps"]
    plan = planner.plan(expected_rps=rollout_target)

    print(f"[scaling] plan for {rollout_target} rps -> {plan.desired_nodes} nodes")

    for request_id in range(5):
        backend = route_request(balancer)
        print(f"[routing] request {request_id} -> {backend.name}")

        def guarded_call() -> str:
            return breaker.call(call_optimizely_model)

        response = graceful_degradation(lambda: retry_with_backoff(guarded_call), lambda _: "serve cached insight")
        print(f"[response] {response}")

        try:
            breaker.call(lambda: None)
        except CircuitOpenError:
            print("[breaker] call blocked due to open circuit")


if __name__ == "__main__":
    main()
