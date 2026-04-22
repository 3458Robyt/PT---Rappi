# Risk Tower UI Redesign Brief

## Skill Direction

Use `ui-ux-pro-max` for a full dashboard redesign, not a cosmetic pass.

## Product Type

Operations risk tower for historical store availability.

## Visual Thesis

Control Tower interface with high-contrast risk signals, Rappi green for healthy operation, amber for budget pressure, red for incidents, cyan/purple for secondary analytical layers.

## Required Information Architecture

- Persistent mission-control rail for date range, hour range, time aggregation, healthy threshold, SLO target, and optional Gemini polishing.
- Top status header that explains range, derived SLI status, healthy threshold, and SLO target.
- KPI strip with Operational SLI, error budget, burn rate, low minutes, incident count, MTTR, MTBF, P10/P90 spread, and recovery velocity.
- Runway time-series chart with moving median, healthy threshold, and incident bands.
- Error budget gauge and incident ranking.
- Hourly heatmap by day and hour.
- Distribution chart with P10/P50/P90 and threshold markers.
- Incident log table.
- Raw filtered data sample.
- Semantic chatbot that answers only about the active filter context.

## UX Requirements

- Make the dashboard understandable by scanning headings, labels, numbers, and chart titles.
- Keep visual hierarchy data-first: metrics and historical chart before chat.
- Do not rely on color alone: charts include labels, legends, markers, and table values.
- Keep controls at least 44px tall where possible.
- Avoid blank or decorative sections.
- Provide CSV export for auditability.
