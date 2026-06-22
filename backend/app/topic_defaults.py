from __future__ import annotations


DEFAULT_TOPICS = [
    {
        "name": "Yankees",
        "priority": 8,
        "source_type": "unstructured",
        "category": "Sports",
        "refresh_frequency": "daily",
        "prompt": "Summarize Yankees results from the previous day. Include next scheduled game and any significant injuries or storylines.",
    },
    {
        "name": "Bitcoin",
        "priority": 9,
        "source_type": "structured",
        "category": "Crypto",
        "refresh_frequency": "daily",
        "prompt": "Summarize Bitcoin movement over the previous 24 hours and identify any major catalysts.",
    },
    {
        "name": "Iran",
        "priority": 7,
        "source_type": "unstructured",
        "category": "Geopolitics",
        "refresh_frequency": "daily",
        "prompt": "Summarize meaningful developments involving Iran from the last 24 hours. Ignore low-impact stories. Focus on military, geopolitical, economic, or global implications.",
    },
    {
        "name": "Major World Sports",
        "priority": 6,
        "source_type": "unstructured",
        "category": "Sports",
        "refresh_frequency": "daily",
        "prompt": "Identify globally significant sporting events beginning within the next 7 days. Include championships, majors, international tournaments, and marquee matchups.",
    },
    {
        "name": "AI",
        "priority": 6,
        "source_type": "unstructured",
        "category": "Technology",
        "refresh_frequency": "daily",
        "prompt": "Summarize meaningful AI developments from the last 24 hours. Ignore routine product announcements unless they change what Mike should pay attention to.",
    },
    {
        "name": "Golf",
        "priority": 5,
        "source_type": "structured",
        "category": "Weather",
        "refresh_frequency": "daily",
        "prompt": "Identify the best golf day this week using weather and schedule constraints. Prefer clear, low-wind days.",
    },
]
