# UI Redesign Brief

## Skill Direction

Use `ui-ux-pro-max` for a full dashboard redesign, not a cosmetic pass.

## Product Type

Operations analytics dashboard for historical store availability.

## Visual Thesis

Dark command-center interface with high-contrast data, Rappi green as the primary signal color, amber for thresholds, red for drops, and cyan for secondary analytical layers.

## Required Information Architecture

- Persistent sidebar filters for date range, hour range, time aggregation, low-availability threshold, event count, table row count, and optional Gemini polishing.
- Top status header that explains range, aggregation, deduplicated points, and overlap count.
- KPI strip with current value, median, minimum, maximum, and point count.
- Historical time-series chart with moving median, low threshold, and event markers.
- Daily chart comparing median, minimum, and maximum.
- Hourly heatmap by day and hour.
- Distribution chart with the low threshold marked.
- Event table ranked by absolute change.
- Daily summary table.
- Low-availability table.
- Raw filtered data sample.
- Semantic chatbot that answers only about the active filter context.

## UX Requirements

- Make the dashboard understandable by scanning headings, labels, numbers, and chart titles.
- Keep visual hierarchy data-first: metrics and historical chart before chat.
- Do not rely on color alone: charts include labels, legends, markers, and table values.
- Keep controls at least 44px tall where possible.
- Avoid blank or decorative sections.
- Provide CSV export for auditability.
