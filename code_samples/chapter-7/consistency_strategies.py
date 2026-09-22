"""
Consistency and Consensus Strategies
------------------------------------

Illustrates event sourcing, read-model projections, and lightweight
consensus flows to balance consistency and availability across regions.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Dict, Iterable, List, MutableMapping


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


@dataclass
class Event:
    aggregate_id: str
    event_type: str
    payload: Dict[str, Any]


class EventLog:
    """Append-only event store representing durable business facts."""

    def __init__(self) -> None:
        self._events: List[Event] = []

    def append(self, event: Event) -> None:
        logging.info("event appended: %s", event)
        self._events.append(event)

    def replay(self) -> List[Event]:
        return list(self._events)


class ReadModel:
    """Eventually consistent read model that materializes projections."""

    def __init__(self) -> None:
        self._state: MutableMapping[str, Any] = {}

    def apply(self, event: Event) -> None:
        document = self._state.setdefault(event.aggregate_id, {})
        document[event.event_type] = event.payload

    def get(self, aggregate_id: str) -> Dict[str, Any]:
        return dict(self._state.get(aggregate_id, {}))


class ConsensusCoordinator:
    """Collect votes from nodes and determine quorum success."""

    def __init__(self, node_ids: Iterable[str], quorum_size: int | None = None) -> None:
        self.node_ids = list(node_ids)
        self.quorum_size = quorum_size or (len(self.node_ids) // 2 + 1)

    def propose(self, proposal_id: str, votes: Dict[str, bool]) -> bool:
        yes_votes = sum(1 for node in self.node_ids if votes.get(node, False))
        logging.info("proposal %s got %s/%s votes", proposal_id, yes_votes, self.quorum_size)
        return yes_votes >= self.quorum_size


def simulate_optimizely_feature_rollout() -> None:
    """Show eventual consistency for global feature toggles."""
    log = EventLog()
    read_model = ReadModel()
    coordinator = ConsensusCoordinator(node_ids=["us", "eu", "apac"])

    event = Event(
        aggregate_id="feature-ai-assist",
        event_type="ROLLED_OUT",
        payload={"enabled_segments": ["enterprise", "beta-testers"], "percentage": 35},
    )

    if coordinator.propose("ai-rollout", votes={"us": True, "eu": True, "apac": False}):
        log.append(event)
        for replay_event in log.replay():
            read_model.apply(replay_event)

    logging.info("read model: %s", read_model.get("feature-ai-assist"))


if __name__ == "__main__":
    simulate_optimizely_feature_rollout()
