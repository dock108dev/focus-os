# ADR 0004: Structured source MVP order

## Status

Accepted.

## Context

The MVP needs real structured data without turning into integration work before the homepage habit is proven.

The documented Tier 1 sources were market prices, crypto, weather, and sports. Weather was called out as especially valuable because “Thursday is the best golf day this week” is exactly the kind of personal attention signal FocusOS should produce.

## Decision

Implement the first structured sources in this order:

1. Yahoo Finance for market prices.
2. CoinGecko for Bitcoin.
3. Open-Meteo for golf weather recommendations.

Open-Meteo is used before OpenWeather or Pirate Weather because it works locally without an API key. OpenWeather and Pirate Weather remain possible replacements if forecast quality becomes a problem.

Sports remains later MVP-adjacent work and should not be implemented before the current homepage behavior is tested.

## Consequences

The app now has enough structured data to produce finance, crypto, and weather attention items.

Source health is stored internally and exposed through `/api/internal/source-status`, but the homepage does not show connector diagnostics.
