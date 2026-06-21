MIKE_PROFILE = {
    "cash_attention_min": 1000,
    "cash_attention_pct": 8,
    "technology_concentration_pct": 45,
    "single_position_concentration_pct": 25,
    "pullback_review_pct": 5,
    "market_move_review_pct": 5,
    "large_cap_pullback_note": "Historically, similar large-cap pullbacks have been worth reviewing before adding capital.",
}


def large_cap_pullback_reason() -> str:
    return (
        "The position crossed the 5% pullback threshold. "
        f"{MIKE_PROFILE['large_cap_pullback_note']}"
    )
