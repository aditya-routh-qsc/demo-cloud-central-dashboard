## Context

The current dashboard frontend renders a centered horizontal tab bar for Overview, Network, Metrics, and Tickets, with a permanently expanded filter strip above it. That layout works, but it is visually dense and leaves limited vertical space for the content panels that actually carry the operational signal. The shell also needs to remain usable across desktop and mobile widths without changing the backend data model or the shared filter semantics already established in the dashboard interface spec.

## Goals / Non-Goals

**Goals:**
- Move the primary view switcher into a left-aligned side navigation on desktop layouts.
- Make advanced search filters collapsible while keeping the primary search field visible.
- Preserve the canonical filter state and current tab/view state across navigation and disclosure changes.
- Keep the responsive experience usable at narrower breakpoints without introducing new backend dependencies.

**Non-Goals:**
- Redesigning the dashboard data APIs or ticket/network payloads.
- Changing the meaning of the existing filter fields or the shared filter model.
- Introducing a second navigation system or duplicate state stores.
- Reworking chart, network, or ticket rendering logic beyond what is needed to fit the new shell.

## Decisions

1. Use a persistent side navigation for desktop view switching.
- Rationale: a vertical rail gives the four core views a stable location, frees horizontal space for content, and is easier to scan when the dashboard grows.
- Alternatives considered:
  - Keep the current centered horizontal tab bar: rejected because it competes with content for vertical space and does not solve the crowded shell problem.
  - Hide navigation behind a menu on desktop: rejected because the four core views are primary, not secondary, destinations.

2. Make advanced filters collapsible rather than removing them.
- Rationale: the search box is the most frequently used filter entry point, while the status, assignee, and board controls are useful but need not occupy constant vertical space.
- Alternatives considered:
  - Keep filters always expanded: rejected because it preserves the current clutter.
  - Move filters into a full-screen drawer: rejected because the controls are used repeatedly and should remain adjacent to the page content.

3. Keep one canonical filter state object in JavaScript.
- Rationale: collapsing or expanding the filter section should affect presentation only; it must not fork state or change query behavior.
- Alternatives considered:
  - Store collapsed filters separately from applied filters: rejected because it adds synchronization complexity and makes resets harder to reason about.
  - Recompute filters from DOM visibility: rejected because the UI state would become fragile.

4. Use a responsive fallback that preserves the same destinations and controls.
- Rationale: mobile and narrow-width users still need access to the same four views and filter actions, but the layout must avoid overflow and dense horizontal grouping.
- Alternatives considered:
  - Hide navigation on mobile: rejected because it would prevent cross-view navigation.
  - Force desktop layout to scale down: rejected because it would make text and controls too small to use comfortably.

## Risks / Trade-offs

- [Risk] Side navigation introduces a wider layout surface that can feel empty on ultra-wide screens. -> Mitigation: constrain the content column width and keep the nav rail compact and sticky.
- [Risk] Collapsible filters can hide important controls from first glance. -> Mitigation: keep the primary search box visible and label the disclosure clearly as advanced filters.
- [Risk] Added disclosure and responsive behavior increase accessibility complexity. -> Mitigation: use explicit button semantics, `aria-expanded`, and keyboard-reachable controls.
- [Risk] Responsive fallback behavior may vary across viewports and browsers. -> Mitigation: validate the shell at desktop, tablet, and mobile breakpoints before release.

## Migration Plan

1. Update the frontend shell markup to separate navigation, filters, and content into clearer structural regions.
2. Rework the CSS layout to support a desktop side rail and a compact narrow-width fallback.
3. Add the collapsible filter interaction while preserving the existing filter state and view selection logic.
4. Update smoke and contract checks to cover the new shell layout and disclosure behavior.
5. Roll out behind the existing dashboard route with no backend API migration.

Rollback strategy:
- Restore the horizontal tab strip and always-expanded filter row if the new shell causes usability or accessibility regressions.
- Keep backend endpoints unchanged so reverting the frontend shell does not require data migration.

## Open Questions

- Should the advanced filter region default to expanded on desktop and collapsed on mobile, or should it remember the user’s last choice?
- Should the side navigation remain sticky as the user scrolls, or stay anchored above the content column?
- Should the compact mobile fallback use a stacked top rail or a collapsible drawer for the four view destinations?
