## Context

The backend already provides Jira release data retrieval through existing `services.py` functions and corresponding API wiring. The current frontend dashboard does not expose this release data in navigation or tab content, which creates a visibility gap for release planning users. This change is constrained to frontend composition and backend contract consumption; Jira-fetch implementation must remain unchanged.

## Goals / Non-Goals

**Goals:**
- Add a first-class `Release` tab to the dashboard navigation model.
- Render a structured table for Jira release records with core fields (name, date, status).
- Reuse existing backend endpoints/contracts that are already powered by `services.py`.
- Keep dashboard behavior documentation aligned with delivered frontend behavior.

**Non-Goals:**
- Rewriting or extending Jira API fetch logic in backend service modules.
- Introducing new backend persistence or schema migrations.
- Redesigning unrelated dashboard tabs or global layout patterns.

## Decisions

1. Introduce Release as a peer tab in existing dashboard navigation.
Rationale: users discover it naturally where other analytical views live, and it reuses existing tab-state handling.
Alternative considered: separate route/page outside tab shell; rejected because it fragments filtering and increases navigation complexity.

2. Build Release content as a dedicated table panel with explicit loading, empty, and error states.
Rationale: release records are naturally tabular and need predictable operator feedback on data availability.
Alternative considered: card-based release tiles; rejected because it degrades scanability for larger release lists.

3. Consume current release-data API response shape without introducing backend changes.
Rationale: backend logic is complete and stable; frontend mapping is sufficient to meet requirements.
Alternative considered: adding a new aggregate endpoint; rejected as unnecessary scope and risk.

4. Keep release tab state independent from existing heavy interaction modules while remaining consistent with global shell behavior.
Rationale: avoids coupling release rendering to dependency graph/ticket explorer internals and minimizes regression risk.
Alternative considered: reuse ticket-table module directly; rejected because release fields and UX differ.

5. Update `docs/CURRENT_BEHAVIOR_SPEC.md` as part of the same implementation cycle.
Rationale: documentation drift has high operational cost; syncing behavior spec during feature delivery keeps audits and onboarding accurate.

## Risks / Trade-offs

- [Risk] Frontend table assumptions may not match all release payload variants. -> Mitigation: implement tolerant field mapping with safe fallbacks and test using representative fixture data.
- [Risk] Adding a tab could impact mobile and narrow-width behavior. -> Mitigation: preserve existing responsive nav patterns and validate Release tab rendering at mobile breakpoints.
- [Trade-off] Reusing existing endpoint contract limits immediate custom sorting/filtering semantics for release-specific fields. -> Mitigation: document future enhancement path; deliver baseline table first.