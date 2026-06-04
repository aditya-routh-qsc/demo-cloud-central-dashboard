## Context

The current dashboard sidebar is always expanded and uses label-only navigation controls, which limits usable width for analytics views and prevents compact workflows. The header already surfaces sync state, but operators need explicit last-update time visibility to quickly assess data freshness. On the backend, scheduled sync cadence is currently not operator-configurable from environment settings, creating deployment friction when teams need faster or slower refresh cycles.

This change spans frontend shell behavior, frontend status display, backend scheduler configuration, and environment/config loading.

## Goals / Non-Goals

**Goals:**
- Introduce a collapsible sidebar with icon-only collapsed mode and icon+text expanded mode.
- Preserve accessibility and active tab behavior regardless of sidebar state.
- Show a clear "last update" timestamp in the shell/header region.
- Make automated scheduled sync/database refresh interval configurable via `.env`.
- Validate interval configuration and fall back to safe default values when invalid or missing.

**Non-Goals:**
- Redesigning all dashboard visual styles beyond sidebar/collapsible behavior.
- Changing network graph rendering semantics or data model.
- Introducing per-user persisted layout preferences across devices.
- Changing API response contracts for core metrics/network/tickets payloads.

## Decisions

1. Sidebar state managed in frontend application state
- Decision: Track `sidebarCollapsed` in frontend state and toggle a root CSS class (for example, `sidebar-collapsed`) to drive layout changes.
- Rationale: Keeps behavior deterministic and minimizes DOM mutation complexity.
- Alternative considered: Directly mutating many element-level inline styles. Rejected because it is harder to maintain and reason about.

2. Icon+label markup in nav buttons
- Decision: Update tab buttons to contain icon and label spans, then hide labels in collapsed mode through CSS.
- Rationale: One semantic control per tab maintains accessibility and keyboard behavior while supporting both visual modes.
- Alternative considered: Separate icon-only and full-text button sets. Rejected due to duplication and risk of state divergence.

3. Last update time sourced from sync status payload
- Decision: Derive last update display from existing sync status fields and show a normalized timestamp in header/sync chip area.
- Rationale: Avoids adding a new endpoint and aligns with current operational data source.
- Alternative considered: Dedicated endpoint for last-update metadata. Rejected as unnecessary contract expansion.

4. Scheduler interval controlled by `.env`
- Decision: Add a dedicated environment variable (for example `SCHEDULED_SYNC_INTERVAL_MINUTES`) and consume it via config utilities with integer parsing and bounds checks.
- Rationale: Enables deployment-time tuning without code edits; centralizes config parsing and validation.
- Alternative considered: Keep hard-coded interval and expose only code-level constant. Rejected because it does not meet operator configurability needs.

## Risks / Trade-offs

- [Invalid `.env` interval values] -> Mitigation: Parse defensively, log warnings, and revert to a tested default interval.
- [Collapsed sidebar reducing discoverability] -> Mitigation: Keep recognizable icons, tooltip/title text, and explicit expand/collapse affordance.
- [Timestamp ambiguity across locales/timezones] -> Mitigation: Use a consistent display format and timezone indicator in UI.
- [Potential layout regressions at small widths] -> Mitigation: Add responsive CSS checks and verify desktop/mobile behavior.

## Migration Plan

- Add new `.env` variable with default example value and document behavior.
- Update config loader to read and validate scheduler interval.
- Update scheduler initialization to use configured interval.
- Deploy backend first (safe default behavior retained), then frontend.
- Rollback strategy: revert to previous release or set `.env` interval to default fallback-compatible value.

## Open Questions

- Exact lower/upper bounds for allowed interval (for example minimum 1 minute, maximum 1440 minutes) to align with operational policy.
- Preferred timestamp format in UI (UTC-only vs localized display with timezone suffix).
