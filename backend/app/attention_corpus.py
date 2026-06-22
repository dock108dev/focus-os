from __future__ import annotations

from .attention_corpus_generation import *  # noqa: F403
from .attention_corpus_models import *  # noqa: F403
from .attention_corpus_quality import *  # noqa: F403
from .attention_corpus_rendering import *  # noqa: F403
from .attention_corpus_scenarios import *  # noqa: F403
from .attention_corpus_simulation import *  # noqa: F403
from .attention_corpus_templates import *  # noqa: F403
from .attention_corpus_watch_data import *  # noqa: F403

__all__ = [name for name in globals() if not name.startswith("_")]


if __name__ == "__main__":
    from .attention_corpus_rendering import main

    main()
