from __future__ import annotations

from .briefing_simulator_helpers import SimulatedScenario
from .briefing_simulator_scenarios_a import SCENARIOS as SCENARIOS_A
from .briefing_simulator_scenarios_b import SCENARIOS as SCENARIOS_B


def scenario_catalog() -> list[SimulatedScenario]:
    return [*SCENARIOS_A, *SCENARIOS_B]
