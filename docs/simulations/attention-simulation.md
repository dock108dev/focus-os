# FocusOS 40-Day Briefing Simulation

Purpose: validate whether ranking and layout assumptions hold across many mornings before changing UI again.

## Summary

- Simulated days: 40
- Layout recommendations: flat=6, major_event=5, quiet=17, single_hero=10, two_lead=2
- Days where a static hero may overstate importance: 25
- Days with scan-rule violations: 6

## Manual Review Questions

For each day, ask:

1. Does the top story deserve top placement?
2. Should the layout have a hero, two leads, or a flat briefing?
3. Are Type B FocusOS stories carrying the value, or is this drifting back into news?
4. Does anything feel overstated or understated?

## Simulated Days

### Day 1: Normal Tuesday

- Notes: Low-signal day where a forced hero would overstate importance.
- Recommended layout: `quiet`
- Why: The day is mostly background context.
- Signal: max=76, avg=51, stories=4, TypeB=2, TypeA=2

- **Today / Life / Consider / focusos**: Wednesday is likely your best golf window this week - Forecast conditions are materially better than the rest of the week.
- **Around You / Technology / Watch / external**: AI policy discussion stayed mostly procedural - Useful context, but not a shift that should dominate the morning.
- **Around You / Sports / Ignore / external**: Yankees won 5-0 - Good result, but no meaningful change to your posture today.
- **Around You / Portfolio / Watch / focusos**: No major portfolio actions currently identified. - No portfolio event is leading the morning brief.

### Day 2: Boring Market Day

- Notes: Portfolio is stable; external context should not inflate the page.
- Recommended layout: `flat`
- Why: No item is strong enough to force a hero; use a flat briefing.
- Signal: max=42, avg=37.3, stories=3, TypeB=2, TypeA=1

- **Around You / Life / Watch / focusos**: Golf forecast remains playable but ordinary - No day is materially better than the rest of the week.
- **Around You / Sports / Ignore / external**: Yankees had a scheduled off day - Good result, but no meaningful change to your posture today.
- **Around You / Portfolio / Watch / focusos**: No major portfolio actions currently identified. - No portfolio event is leading the morning brief.

### Day 3: Market Crash Day

- Notes: Major portfolio day where a dominant hero is justified.
- Recommended layout: `major_event`
- Why: One signal is strong enough to dominate the whole page.
- Signal: max=96, avg=66, stories=2, TypeB=1, TypeA=1
- Scan issues: Homepage story count must be 3-7; got 2.

- **Today / Portfolio / Review / focusos**: Review portfolio positioning - 4 portfolio signals crossed review thresholds. Technology concentration is above target. 2 are opportunities, not separate homepage stories.
- **Around You / Sports / Ignore / external**: Yankees won 4-2 - Good result, but no meaningful change to your posture today.

### Day 4: Crypto Crash Day

- Notes: Crypto should matter only when it changes the user's portfolio posture.
- Recommended layout: `single_hero`
- Why: A single high-signal item deserves a hero treatment.
- Signal: max=86, avg=62, stories=2, TypeB=1, TypeA=1
- Scan issues: Homepage story count must be 3-7; got 2.

- **Today / Portfolio / Review / focusos**: Portfolio opportunity window is open - 3 portfolio signals crossed review thresholds.
- **Around You / Technology / Watch / external**: AI product launches were routine - No material change to the AI landscape.

### Day 5: No News Day

- Notes: Tests whether the layout can avoid inventing a hero.
- Recommended layout: `flat`
- Why: No item is strong enough to force a hero; use a flat briefing.
- Signal: max=36, avg=35, stories=3, TypeB=2, TypeA=1

- **Around You / Life / Watch / focusos**: Golf forecast is ordinary this week - No day stands out enough to plan around.
- **Around You / Portfolio / Watch / focusos**: No major portfolio actions currently identified. - No portfolio event is leading the morning brief.
- **Around You / Sports / Ignore / external**: Yankees schedule is quiet - Good result, but no meaningful change to your posture today.

### Day 6: Golf Weather Week

- Notes: A Type B life-planning item should lead if portfolio is quiet.
- Recommended layout: `quiet`
- Why: The day is mostly background context.
- Signal: max=82, avg=52.3, stories=3, TypeB=2, TypeA=1

- **Today / Life / Consider / focusos**: Thursday is likely your best golf window this month - Forecast conditions are materially better than the rest of the ten-day window.
- **Around You / Technology / Watch / external**: AI funding news stayed incremental - No major capability or access shift.
- **Around You / Portfolio / Watch / focusos**: No major portfolio actions currently identified. - No portfolio event is leading the morning brief.

### Day 7: Yankees Playoff Clinch

- Notes: Sports can matter when it changes context, but should not feel like a task.
- Recommended layout: `quiet`
- Why: The day is mostly background context.
- Signal: max=72, avg=49.7, stories=3, TypeB=2, TypeA=1

- **Around You / Sports / Watch / external**: Yankees clinched a playoff spot - This changes the season context and upcoming stakes.
- **Around You / Life / Watch / focusos**: Weekend golf weather is playable - Conditions are fine but not meaningfully better than alternatives.
- **Around You / Portfolio / Watch / focusos**: No major portfolio actions currently identified. - No portfolio event is leading the morning brief.

### Day 8: Yankees Routine Win

- Notes: Routine sports reporting should recede or be omitted.
- Recommended layout: `quiet`
- Why: The day is mostly background context.
- Signal: max=76, avg=48.2, stories=4, TypeB=2, TypeA=2

- **Today / Life / Consider / focusos**: Wednesday is likely your best golf window this week - Forecast conditions are better than the rest of the week.
- **Around You / Technology / Watch / external**: AI regulation discussion stayed unresolved - Worth tracking, but no new decision context.
- **Around You / Sports / Ignore / external**: Yankees won 6-3 - Good result, but no meaningful change to your posture today.
- **Around You / Portfolio / Watch / focusos**: No major portfolio actions currently identified. - No portfolio event is leading the morning brief.

### Day 9: Rutgers Game Week

- Notes: A personal calendar-adjacent item should outrank generic news.
- Recommended layout: `quiet`
- Why: The day is mostly background context.
- Signal: max=84, avg=51.7, stories=3, TypeB=2, TypeA=1

- **Today / Rutgers / Review / focusos**: Rutgers game week needs a plan - Kickoff, travel, and ticket timing make this a real planning item.
- **Around You / Sports / Ignore / external**: Yankees won 5-4 - Good result, but no meaningful change to your posture today.
- **Around You / Portfolio / Watch / focusos**: No major portfolio actions currently identified. - No portfolio event is leading the morning brief.

### Day 10: Rutgers Tickets Renew Friday

- Notes: Deadline-like personal item should be Today, but not corporate.
- Recommended layout: `single_hero`
- Why: A single high-signal item deserves a hero treatment.
- Signal: max=88, avg=49.2, stories=4, TypeB=3, TypeA=1

- **Today / Rutgers / Review / focusos**: Rutgers tickets renew Friday - The window closes soon, so this belongs on your radar today.
- **Around You / Technology / Watch / external**: AI model news was incremental - No major access or capability shift.
- **Around You / Portfolio / Watch / focusos**: No major portfolio actions currently identified. - No portfolio event is leading the morning brief.
- **Around You / Life / Watch / focusos**: Golf weather is ordinary - No day is clearly better than the rest.

### Day 11: Vacation Week

- Notes: Travel planning should lead when dates create risk.
- Recommended layout: `single_hero`
- Why: A single high-signal item deserves a hero treatment.
- Signal: max=86, avg=52.3, stories=3, TypeB=2, TypeA=1

- **Today / Travel / Review / focusos**: Vacation departure needs a travel check - Weather and airport timing could affect departure planning.
- **Around You / Sports / Ignore / external**: Yankees start a normal series - Good result, but no meaningful change to your posture today.
- **Around You / Portfolio / Watch / focusos**: No major portfolio actions currently identified. - No portfolio event is leading the morning brief.

### Day 12: Busy Work Week

- Notes: Work context should dominate only if inactivity or deadline signals exist.
- Recommended layout: `two_lead`
- Why: Two meaningful items should share the top of the page.
- Signal: max=84, avg=57.2, stories=4, TypeB=3, TypeA=1

- **Today / Work / Review / focusos**: Two projects have been inactive for 10 days - This may create hidden drag if it is not reviewed.
- **Today / Life / Consider / focusos**: Wednesday is a good golf window - Good weather exists, but work context may constrain timing.
- **Around You / Technology / Watch / external**: AI policy news remains background - Worth knowing, not a near-term decision.
- **Around You / Portfolio / Watch / focusos**: No major portfolio actions currently identified. - No portfolio event is leading the morning brief.

### Day 13: Ai Breakthrough Day

- Notes: External news can lead if the signal is genuinely high.
- Recommended layout: `single_hero`
- Why: A single high-signal item deserves a hero treatment.
- Signal: max=88, avg=52.3, stories=3, TypeB=2, TypeA=1

- **Around You / Technology / Watch / external**: AI capability jump changes tool landscape - A major model release may affect which tools are worth using this week.
- **Around You / Portfolio / Watch / focusos**: No major portfolio actions currently identified. - No portfolio event is leading the morning brief.
- **Around You / Life / Watch / focusos**: Golf forecast is ordinary - No strong planning window emerged.

### Day 14: Iran Escalation Day

- Notes: World news should be Background unless it changes practical posture.
- Recommended layout: `quiet`
- Why: The day is mostly background context.
- Signal: max=76, avg=49, stories=3, TypeB=1, TypeA=2

- **Background / World / Watch / external**: Iran escalation raises oil and travel risk - The situation may affect markets and travel planning, but no personal action is implied yet.
- **Around You / Sports / Ignore / external**: Yankees won 2-1 - Good result, but no meaningful change to your posture today.
- **Around You / Portfolio / Watch / focusos**: No major portfolio actions currently identified. - No portfolio event is leading the morning brief.

### Day 15: Major Event Day

- Notes: Single external event may justify one dominant story.
- Recommended layout: `major_event`
- Why: One signal is strong enough to dominate the whole page.
- Signal: max=98, avg=73.3, stories=3, TypeB=2, TypeA=1

- **Today / Portfolio / Review / focusos**: Review portfolio positioning - 1 portfolio signals crossed review thresholds.
- **Today / Travel / Review / focusos**: Travel advisory issued for vacation route - The advisory could affect departure timing.
- **Around You / Sports / Ignore / external**: Yankees game postponed - Good result, but no meaningful change to your posture today.

### Day 16: Normal Tuesday

- Notes: Low-signal day where a forced hero would overstate importance.
- Recommended layout: `quiet`
- Why: The day is mostly background context.
- Signal: max=76, avg=51, stories=4, TypeB=2, TypeA=2

- **Today / Life / Consider / focusos**: Wednesday is likely your best golf window this week - Forecast conditions are materially better than the rest of the week.
- **Around You / Technology / Watch / external**: AI policy discussion stayed mostly procedural - Useful context, but not a shift that should dominate the morning.
- **Around You / Sports / Ignore / external**: Yankees won 5-0 - Good result, but no meaningful change to your posture today.
- **Around You / Portfolio / Watch / focusos**: No major portfolio actions currently identified. - No portfolio event is leading the morning brief.

### Day 17: Boring Market Day

- Notes: Portfolio is stable; external context should not inflate the page.
- Recommended layout: `flat`
- Why: No item is strong enough to force a hero; use a flat briefing.
- Signal: max=42, avg=37.3, stories=3, TypeB=2, TypeA=1

- **Around You / Life / Watch / focusos**: Golf forecast remains playable but ordinary - No day is materially better than the rest of the week.
- **Around You / Sports / Ignore / external**: Yankees had a scheduled off day - Good result, but no meaningful change to your posture today.
- **Around You / Portfolio / Watch / focusos**: No major portfolio actions currently identified. - No portfolio event is leading the morning brief.

### Day 18: Market Crash Day

- Notes: Major portfolio day where a dominant hero is justified.
- Recommended layout: `major_event`
- Why: One signal is strong enough to dominate the whole page.
- Signal: max=96, avg=66, stories=2, TypeB=1, TypeA=1
- Scan issues: Homepage story count must be 3-7; got 2.

- **Today / Portfolio / Review / focusos**: Review portfolio positioning - 4 portfolio signals crossed review thresholds. Technology concentration is above target. 2 are opportunities, not separate homepage stories.
- **Around You / Sports / Ignore / external**: Yankees won 4-2 - Good result, but no meaningful change to your posture today.

### Day 19: Crypto Crash Day

- Notes: Crypto should matter only when it changes the user's portfolio posture.
- Recommended layout: `single_hero`
- Why: A single high-signal item deserves a hero treatment.
- Signal: max=86, avg=62, stories=2, TypeB=1, TypeA=1
- Scan issues: Homepage story count must be 3-7; got 2.

- **Today / Portfolio / Review / focusos**: Portfolio opportunity window is open - 3 portfolio signals crossed review thresholds.
- **Around You / Technology / Watch / external**: AI product launches were routine - No material change to the AI landscape.

### Day 20: No News Day

- Notes: Tests whether the layout can avoid inventing a hero.
- Recommended layout: `flat`
- Why: No item is strong enough to force a hero; use a flat briefing.
- Signal: max=36, avg=35, stories=3, TypeB=2, TypeA=1

- **Around You / Life / Watch / focusos**: Golf forecast is ordinary this week - No day stands out enough to plan around.
- **Around You / Portfolio / Watch / focusos**: No major portfolio actions currently identified. - No portfolio event is leading the morning brief.
- **Around You / Sports / Ignore / external**: Yankees schedule is quiet - Good result, but no meaningful change to your posture today.

### Day 21: Golf Weather Week

- Notes: A Type B life-planning item should lead if portfolio is quiet.
- Recommended layout: `quiet`
- Why: The day is mostly background context.
- Signal: max=82, avg=52.3, stories=3, TypeB=2, TypeA=1

- **Today / Life / Consider / focusos**: Thursday is likely your best golf window this month - Forecast conditions are materially better than the rest of the ten-day window.
- **Around You / Technology / Watch / external**: AI funding news stayed incremental - No major capability or access shift.
- **Around You / Portfolio / Watch / focusos**: No major portfolio actions currently identified. - No portfolio event is leading the morning brief.

### Day 22: Yankees Playoff Clinch

- Notes: Sports can matter when it changes context, but should not feel like a task.
- Recommended layout: `quiet`
- Why: The day is mostly background context.
- Signal: max=72, avg=49.7, stories=3, TypeB=2, TypeA=1

- **Around You / Sports / Watch / external**: Yankees clinched a playoff spot - This changes the season context and upcoming stakes.
- **Around You / Life / Watch / focusos**: Weekend golf weather is playable - Conditions are fine but not meaningfully better than alternatives.
- **Around You / Portfolio / Watch / focusos**: No major portfolio actions currently identified. - No portfolio event is leading the morning brief.

### Day 23: Yankees Routine Win

- Notes: Routine sports reporting should recede or be omitted.
- Recommended layout: `quiet`
- Why: The day is mostly background context.
- Signal: max=76, avg=48.2, stories=4, TypeB=2, TypeA=2

- **Today / Life / Consider / focusos**: Wednesday is likely your best golf window this week - Forecast conditions are better than the rest of the week.
- **Around You / Technology / Watch / external**: AI regulation discussion stayed unresolved - Worth tracking, but no new decision context.
- **Around You / Sports / Ignore / external**: Yankees won 6-3 - Good result, but no meaningful change to your posture today.
- **Around You / Portfolio / Watch / focusos**: No major portfolio actions currently identified. - No portfolio event is leading the morning brief.

### Day 24: Rutgers Game Week

- Notes: A personal calendar-adjacent item should outrank generic news.
- Recommended layout: `quiet`
- Why: The day is mostly background context.
- Signal: max=84, avg=51.7, stories=3, TypeB=2, TypeA=1

- **Today / Rutgers / Review / focusos**: Rutgers game week needs a plan - Kickoff, travel, and ticket timing make this a real planning item.
- **Around You / Sports / Ignore / external**: Yankees won 5-4 - Good result, but no meaningful change to your posture today.
- **Around You / Portfolio / Watch / focusos**: No major portfolio actions currently identified. - No portfolio event is leading the morning brief.

### Day 25: Rutgers Tickets Renew Friday

- Notes: Deadline-like personal item should be Today, but not corporate.
- Recommended layout: `single_hero`
- Why: A single high-signal item deserves a hero treatment.
- Signal: max=88, avg=49.2, stories=4, TypeB=3, TypeA=1

- **Today / Rutgers / Review / focusos**: Rutgers tickets renew Friday - The window closes soon, so this belongs on your radar today.
- **Around You / Technology / Watch / external**: AI model news was incremental - No major access or capability shift.
- **Around You / Portfolio / Watch / focusos**: No major portfolio actions currently identified. - No portfolio event is leading the morning brief.
- **Around You / Life / Watch / focusos**: Golf weather is ordinary - No day is clearly better than the rest.

### Day 26: Vacation Week

- Notes: Travel planning should lead when dates create risk.
- Recommended layout: `single_hero`
- Why: A single high-signal item deserves a hero treatment.
- Signal: max=86, avg=52.3, stories=3, TypeB=2, TypeA=1

- **Today / Travel / Review / focusos**: Vacation departure needs a travel check - Weather and airport timing could affect departure planning.
- **Around You / Sports / Ignore / external**: Yankees start a normal series - Good result, but no meaningful change to your posture today.
- **Around You / Portfolio / Watch / focusos**: No major portfolio actions currently identified. - No portfolio event is leading the morning brief.

### Day 27: Busy Work Week

- Notes: Work context should dominate only if inactivity or deadline signals exist.
- Recommended layout: `two_lead`
- Why: Two meaningful items should share the top of the page.
- Signal: max=84, avg=57.2, stories=4, TypeB=3, TypeA=1

- **Today / Work / Review / focusos**: Two projects have been inactive for 10 days - This may create hidden drag if it is not reviewed.
- **Today / Life / Consider / focusos**: Wednesday is a good golf window - Good weather exists, but work context may constrain timing.
- **Around You / Technology / Watch / external**: AI policy news remains background - Worth knowing, not a near-term decision.
- **Around You / Portfolio / Watch / focusos**: No major portfolio actions currently identified. - No portfolio event is leading the morning brief.

### Day 28: Ai Breakthrough Day

- Notes: External news can lead if the signal is genuinely high.
- Recommended layout: `single_hero`
- Why: A single high-signal item deserves a hero treatment.
- Signal: max=88, avg=52.3, stories=3, TypeB=2, TypeA=1

- **Around You / Technology / Watch / external**: AI capability jump changes tool landscape - A major model release may affect which tools are worth using this week.
- **Around You / Portfolio / Watch / focusos**: No major portfolio actions currently identified. - No portfolio event is leading the morning brief.
- **Around You / Life / Watch / focusos**: Golf forecast is ordinary - No strong planning window emerged.

### Day 29: Iran Escalation Day

- Notes: World news should be Background unless it changes practical posture.
- Recommended layout: `quiet`
- Why: The day is mostly background context.
- Signal: max=76, avg=49, stories=3, TypeB=1, TypeA=2

- **Background / World / Watch / external**: Iran escalation raises oil and travel risk - The situation may affect markets and travel planning, but no personal action is implied yet.
- **Around You / Sports / Ignore / external**: Yankees won 2-1 - Good result, but no meaningful change to your posture today.
- **Around You / Portfolio / Watch / focusos**: No major portfolio actions currently identified. - No portfolio event is leading the morning brief.

### Day 30: Major Event Day

- Notes: Single external event may justify one dominant story.
- Recommended layout: `major_event`
- Why: One signal is strong enough to dominate the whole page.
- Signal: max=98, avg=73.3, stories=3, TypeB=2, TypeA=1

- **Today / Portfolio / Review / focusos**: Review portfolio positioning - 1 portfolio signals crossed review thresholds.
- **Today / Travel / Review / focusos**: Travel advisory issued for vacation route - The advisory could affect departure timing.
- **Around You / Sports / Ignore / external**: Yankees game postponed - Good result, but no meaningful change to your posture today.

### Day 31: Normal Tuesday

- Notes: Low-signal day where a forced hero would overstate importance.
- Recommended layout: `quiet`
- Why: The day is mostly background context.
- Signal: max=76, avg=51, stories=4, TypeB=2, TypeA=2

- **Today / Life / Consider / focusos**: Wednesday is likely your best golf window this week - Forecast conditions are materially better than the rest of the week.
- **Around You / Technology / Watch / external**: AI policy discussion stayed mostly procedural - Useful context, but not a shift that should dominate the morning.
- **Around You / Sports / Ignore / external**: Yankees won 5-0 - Good result, but no meaningful change to your posture today.
- **Around You / Portfolio / Watch / focusos**: No major portfolio actions currently identified. - No portfolio event is leading the morning brief.

### Day 32: Boring Market Day

- Notes: Portfolio is stable; external context should not inflate the page.
- Recommended layout: `flat`
- Why: No item is strong enough to force a hero; use a flat briefing.
- Signal: max=42, avg=37.3, stories=3, TypeB=2, TypeA=1

- **Around You / Life / Watch / focusos**: Golf forecast remains playable but ordinary - No day is materially better than the rest of the week.
- **Around You / Sports / Ignore / external**: Yankees had a scheduled off day - Good result, but no meaningful change to your posture today.
- **Around You / Portfolio / Watch / focusos**: No major portfolio actions currently identified. - No portfolio event is leading the morning brief.

### Day 33: Market Crash Day

- Notes: Major portfolio day where a dominant hero is justified.
- Recommended layout: `major_event`
- Why: One signal is strong enough to dominate the whole page.
- Signal: max=96, avg=66, stories=2, TypeB=1, TypeA=1
- Scan issues: Homepage story count must be 3-7; got 2.

- **Today / Portfolio / Review / focusos**: Review portfolio positioning - 4 portfolio signals crossed review thresholds. Technology concentration is above target. 2 are opportunities, not separate homepage stories.
- **Around You / Sports / Ignore / external**: Yankees won 4-2 - Good result, but no meaningful change to your posture today.

### Day 34: Crypto Crash Day

- Notes: Crypto should matter only when it changes the user's portfolio posture.
- Recommended layout: `single_hero`
- Why: A single high-signal item deserves a hero treatment.
- Signal: max=86, avg=62, stories=2, TypeB=1, TypeA=1
- Scan issues: Homepage story count must be 3-7; got 2.

- **Today / Portfolio / Review / focusos**: Portfolio opportunity window is open - 3 portfolio signals crossed review thresholds.
- **Around You / Technology / Watch / external**: AI product launches were routine - No material change to the AI landscape.

### Day 35: No News Day

- Notes: Tests whether the layout can avoid inventing a hero.
- Recommended layout: `flat`
- Why: No item is strong enough to force a hero; use a flat briefing.
- Signal: max=36, avg=35, stories=3, TypeB=2, TypeA=1

- **Around You / Life / Watch / focusos**: Golf forecast is ordinary this week - No day stands out enough to plan around.
- **Around You / Portfolio / Watch / focusos**: No major portfolio actions currently identified. - No portfolio event is leading the morning brief.
- **Around You / Sports / Ignore / external**: Yankees schedule is quiet - Good result, but no meaningful change to your posture today.

### Day 36: Golf Weather Week

- Notes: A Type B life-planning item should lead if portfolio is quiet.
- Recommended layout: `quiet`
- Why: The day is mostly background context.
- Signal: max=82, avg=52.3, stories=3, TypeB=2, TypeA=1

- **Today / Life / Consider / focusos**: Thursday is likely your best golf window this month - Forecast conditions are materially better than the rest of the ten-day window.
- **Around You / Technology / Watch / external**: AI funding news stayed incremental - No major capability or access shift.
- **Around You / Portfolio / Watch / focusos**: No major portfolio actions currently identified. - No portfolio event is leading the morning brief.

### Day 37: Yankees Playoff Clinch

- Notes: Sports can matter when it changes context, but should not feel like a task.
- Recommended layout: `quiet`
- Why: The day is mostly background context.
- Signal: max=72, avg=49.7, stories=3, TypeB=2, TypeA=1

- **Around You / Sports / Watch / external**: Yankees clinched a playoff spot - This changes the season context and upcoming stakes.
- **Around You / Life / Watch / focusos**: Weekend golf weather is playable - Conditions are fine but not meaningfully better than alternatives.
- **Around You / Portfolio / Watch / focusos**: No major portfolio actions currently identified. - No portfolio event is leading the morning brief.

### Day 38: Yankees Routine Win

- Notes: Routine sports reporting should recede or be omitted.
- Recommended layout: `quiet`
- Why: The day is mostly background context.
- Signal: max=76, avg=48.2, stories=4, TypeB=2, TypeA=2

- **Today / Life / Consider / focusos**: Wednesday is likely your best golf window this week - Forecast conditions are better than the rest of the week.
- **Around You / Technology / Watch / external**: AI regulation discussion stayed unresolved - Worth tracking, but no new decision context.
- **Around You / Sports / Ignore / external**: Yankees won 6-3 - Good result, but no meaningful change to your posture today.
- **Around You / Portfolio / Watch / focusos**: No major portfolio actions currently identified. - No portfolio event is leading the morning brief.

### Day 39: Rutgers Game Week

- Notes: A personal calendar-adjacent item should outrank generic news.
- Recommended layout: `quiet`
- Why: The day is mostly background context.
- Signal: max=84, avg=51.7, stories=3, TypeB=2, TypeA=1

- **Today / Rutgers / Review / focusos**: Rutgers game week needs a plan - Kickoff, travel, and ticket timing make this a real planning item.
- **Around You / Sports / Ignore / external**: Yankees won 5-4 - Good result, but no meaningful change to your posture today.
- **Around You / Portfolio / Watch / focusos**: No major portfolio actions currently identified. - No portfolio event is leading the morning brief.

### Day 40: Rutgers Tickets Renew Friday

- Notes: Deadline-like personal item should be Today, but not corporate.
- Recommended layout: `single_hero`
- Why: A single high-signal item deserves a hero treatment.
- Signal: max=88, avg=49.2, stories=4, TypeB=3, TypeA=1

- **Today / Rutgers / Review / focusos**: Rutgers tickets renew Friday - The window closes soon, so this belongs on your radar today.
- **Around You / Technology / Watch / external**: AI model news was incremental - No major access or capability shift.
- **Around You / Portfolio / Watch / focusos**: No major portfolio actions currently identified. - No portfolio event is leading the morning brief.
- **Around You / Life / Watch / focusos**: Golf weather is ordinary - No day is clearly better than the rest.

