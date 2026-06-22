from __future__ import annotations

from .attention_corpus_models import AttentionScenario
from .attention_corpus_scenarios_a import SCENARIOS_A
from .attention_corpus_scenarios_b import SCENARIOS_B


SCENARIOS: tuple[AttentionScenario, ...] = (*SCENARIOS_A, *SCENARIOS_B)
