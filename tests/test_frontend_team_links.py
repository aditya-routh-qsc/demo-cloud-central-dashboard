from __future__ import annotations

from pathlib import Path
import unittest


class FrontendTeamLinksContractTests(unittest.TestCase):
    def test_team_detail_header_renders_plain_text_title(self) -> None:
        app_js = Path("frontend/app.js").read_text(encoding="utf-8")

        self.assertIn('el.teamDetailTitle.textContent = `${teamName} Details`', app_js)
        self.assertNotIn("renderTeamNameExternalLink", app_js)
        self.assertNotIn("selectedTeam.team_profile_url", app_js)
        self.assertNotIn("team-detail-title-link", app_js)

    def test_team_detail_styles_include_table_layout(self) -> None:
        style_css = Path("frontend/style.css").read_text(encoding="utf-8")

        self.assertIn(".team-meta-row", style_css)
        self.assertIn(".team-member-table", style_css)
        self.assertIn(".team-member-table-wrap", style_css)
        self.assertIn(".team-detail-stack", style_css)
        self.assertIn(".team-detail-panel", style_css)
        self.assertNotIn(".team-name-link", style_css)
        self.assertNotIn(".team-detail-title-link", style_css)

    def test_team_and_infocomm_tabs_hide_filter_controls_and_ignore_filter_queries(self) -> None:
        app_js = Path("frontend/app.js").read_text(encoding="utf-8")

        self.assertIn('tabName === "teams" || tabName === "infocomm" || tabName === "release"', app_js)
        self.assertIn("controlToolbar", app_js)
        self.assertIn('classList.remove("control-toolbar", "panel")', app_js)
        self.assertIn('classList.add("control-toolbar", "panel")', app_js)
        self.assertIn("el.controlToolbar.hidden = hideFilters", app_js)
        self.assertIn('apiGet("/api/teams")', app_js)

    def test_overview_and_tickets_search_panel_defaults_to_collapsed(self) -> None:
        app_js = Path("frontend/app.js").read_text(encoding="utf-8")
        index_html = Path("frontend/index.html").read_text(encoding="utf-8")

        self.assertIn("advancedFiltersOpen: false", app_js)
        self.assertIn('id="toggleAdvancedFiltersBtn"', index_html)
        self.assertIn('aria-expanded="false"', index_html)
        self.assertIn('id="advancedFilters" class="filters-advanced panel is-collapsed"', index_html)
        self.assertIn("hidden", index_html)

    def test_overview_panel_contains_reflect_and_report_links(self) -> None:
        index_html = Path("frontend/index.html").read_text(encoding="utf-8")
        style_css = Path("frontend/style.css").read_text(encoding="utf-8")

        self.assertIn('id="overviewUsefulLinksPanel"', index_html)
        self.assertIn("Reflect Environments", index_html)
        self.assertIn("Automation Reports", index_html)
        self.assertIn("Grafana Dashboards", index_html)
        self.assertIn("https://dev.reflect.qsc.com", index_html)
        self.assertIn("https://reflect.qsc.com", index_html)
        self.assertIn("https://dev.azure.com/qsys-dev/AutomatedTesting/_build/results?buildId=24879&view=qameta.allure-azure-pipelines.build-allure-tab", index_html)
        self.assertIn("https://grqremqscwus21prod-ewbgazfae4ebcbdv.wus2.grafana.azure.com", index_html)
        self.assertIn('target="_blank"', index_html)
        self.assertIn('rel="noopener noreferrer"', index_html)
        self.assertIn(".overview-links-panel", style_css)
        self.assertIn(".overview-links-table", style_css)

    def test_release_tab_renders_table_and_fetches_existing_release_endpoint(self) -> None:
        app_js = Path("frontend/app.js").read_text(encoding="utf-8")
        index_html = Path("frontend/index.html").read_text(encoding="utf-8")

        self.assertIn('data-tab="release"', index_html)
        self.assertIn('id="releaseTableBody"', index_html)
        self.assertIn('data-release-sort-key="name"', index_html)
        self.assertIn('data-release-sort-key="releaseDate"', index_html)
        self.assertIn('data-release-sort-key="status"', index_html)
        self.assertIn('id="releaseNameFilterInput"', index_html)
        self.assertIn('id="releaseStatusFilterSelect"', index_html)
        self.assertIn('id="releaseClearFiltersBtn"', index_html)
        self.assertIn('id="releaseEditToggleBtn"', index_html)
        self.assertIn('id="releaseEditModal"', index_html)
        self.assertIn('id="releaseModalDependsTabBtn"', index_html)
        self.assertIn('id="releaseModalDependedByTabBtn"', index_html)
        self.assertIn('id="releaseModalAddBtn"', index_html)
        self.assertIn('id="releaseModalApplyBtn"', index_html)
        self.assertIn('id="releaseModalResetBtn"', index_html)
        self.assertIn('id="releaseSelectAllCheckbox"', index_html)
        self.assertIn('id="releaseGraphToggleBtn"', index_html)
        self.assertIn('id="releaseGraphPanel"', index_html)
        self.assertIn('id="releaseGraphStatusFilter"', index_html)
        self.assertIn('id="releaseGraphCanvas"', index_html)
        self.assertIn("cytoscape.min.js", index_html)
        self.assertIn("release-sort-indicator", index_html)
        self.assertIn("Release Name", index_html)
        self.assertIn("Release Date", index_html)
        self.assertIn("Status", index_html)
        self.assertIn('apiGet("/api/releases")', app_js)
        self.assertIn("Loading release data...", app_js)
        self.assertIn("No releases available.", app_js)
        self.assertIn("Failed to load release data:", app_js)
        self.assertIn("normalizeReleaseRows", app_js)

    def test_release_table_sorting_uses_tristate_header_cycle_and_active_indicators(self) -> None:
        app_js = Path("frontend/app.js").read_text(encoding="utf-8")
        style_css = Path("frontend/style.css").read_text(encoding="utf-8")

        self.assertIn("cycleSortDirection", app_js)
        self.assertIn('return "asc"', app_js)
        self.assertIn('return "desc"', app_js)
        self.assertIn('return "none"', app_js)
        self.assertIn("handleReleaseSortHeaderClick", app_js)
        self.assertIn("renderReleaseSortIndicators", app_js)
        self.assertIn('button.classList.toggle("is-active", isActive)', app_js)
        self.assertIn('button.setAttribute("aria-sort", ariaSort)', app_js)
        self.assertIn(".release-sort-button", style_css)
        self.assertIn(".release-sort-button.is-active", style_css)

    def test_release_date_sorting_is_date_aware_and_restores_unsorted_baseline(self) -> None:
        app_js = Path("frontend/app.js").read_text(encoding="utf-8")

        self.assertIn("parseReleaseDateMillis", app_js)
        self.assertIn("Date.parse(value)", app_js)
        self.assertIn('columnKey === "releaseDate"', app_js)
        self.assertIn("leftMillis - rightMillis", app_js)
        self.assertIn("left.index - right.index", app_js)
        self.assertIn('direction === "none"', app_js)
        self.assertIn("return rows", app_js)

    def test_release_table_supports_name_and_status_filters(self) -> None:
        app_js = Path("frontend/app.js").read_text(encoding="utf-8")
        style_css = Path("frontend/style.css").read_text(encoding="utf-8")

        self.assertIn("getFilteredReleaseRows", app_js)
        self.assertIn("renderReleaseStatusFilterOptions", app_js)
        self.assertIn('state.release.filters.nameQuery', app_js)
        self.assertIn('state.release.filters.status', app_js)
        self.assertIn("No releases match current filters.", app_js)
        self.assertIn("releaseNameFilterInput", app_js)
        self.assertIn("releaseStatusFilterSelect", app_js)
        self.assertIn("releaseClearFiltersBtn", app_js)
        self.assertIn('status === "Planned" && rowStatus === "Overdue"', app_js)
        self.assertIn('if (statusSet.has("Planned") || statusSet.has("Overdue"))', app_js)
        self.assertIn(".release-table-filters", style_css)

    def test_release_relationship_api_persistence_and_reconciliation_are_present(self) -> None:
        app_js = Path("frontend/app.js").read_text(encoding="utf-8")

        self.assertIn("loadReleaseRelationshipsFromApi", app_js)
        self.assertIn("saveReleaseRelationshipsToApi", app_js)
        self.assertIn("normalizeReleaseRelationshipMap", app_js)
        self.assertIn('"/api/releases/relationships"', app_js)
        self.assertIn("scrubReleaseRelationshipsAgainstRows", app_js)
        self.assertIn("co_releases", app_js)
        self.assertIn("depends_on", app_js)

    def test_release_graph_panel_and_status_filter_rendering_are_present(self) -> None:
        app_js = Path("frontend/app.js").read_text(encoding="utf-8")
        index_html = Path("frontend/index.html").read_text(encoding="utf-8")
        style_css = Path("frontend/style.css").read_text(encoding="utf-8")

        self.assertIn("renderReleaseGraph", app_js)
        self.assertIn("window.cytoscape", app_js)
        self.assertIn("buildReleaseCoReleaseGroups", app_js)
        self.assertIn("getReleaseGraphRenderableIds", app_js)
        self.assertIn("syncReleasePanelVisibility", app_js)
        self.assertIn("state.release.graph.statusFilter", app_js)
        self.assertIn('statusFilter: ["Released", "Planned"]', app_js)
        self.assertIn('status === "Overdue" && selectedStatuses.has("Planned")', app_js)
        self.assertIn("status-planned", app_js)
        self.assertIn("status-overdue", app_js)
        self.assertIn('id="releaseGraphStatusFilter"', index_html)
        self.assertIn('<option value="Released" selected>Released</option>', index_html)
        self.assertIn('<option value="Planned" selected>Planned</option>', index_html)
        self.assertNotIn('<option value="Archived" selected>Archived</option>', index_html)
        self.assertNotIn('<option value="Overdue" selected>Overdue</option>', index_html)
        self.assertIn(".release-graph-panel", style_css)
        self.assertIn(".release-graph-canvas", style_css)

    def test_release_edit_mode_and_suggestion_pickers_are_present(self) -> None:
        app_js = Path("frontend/app.js").read_text(encoding="utf-8")
        style_css = Path("frontend/style.css").read_text(encoding="utf-8")

        self.assertIn("openReleaseEditModal", app_js)
        self.assertIn("renderReleaseEditModal", app_js)
        self.assertIn("applyReleaseModalAddSubmit", app_js)
        self.assertIn("applyReleaseModalRemoveRow", app_js)
        self.assertIn("applyReleaseModalChanges", app_js)
        self.assertIn("state.release.modal.activeTab", app_js)
        self.assertIn("releaseModalApplyBtn", app_js)
        self.assertIn("Edit", app_js)
        self.assertIn("selectedCount === 0", app_js)
        self.assertIn("releaseEditToggleBtn.hidden = selectedCount === 0", app_js)
        self.assertIn("Select at least one release row to open dependency editor", app_js)
        self.assertIn(".release-edit-modal", style_css)
        self.assertIn(".release-modal-tab", style_css)
        self.assertIn(".release-modal-remove-btn", style_css)

    def test_release_status_cells_have_theme_aligned_color_classes(self) -> None:
        app_js = Path("frontend/app.js").read_text(encoding="utf-8")
        style_css = Path("frontend/style.css").read_text(encoding="utf-8")

        self.assertIn("getReleaseStatusClass", app_js)
        self.assertIn("release-status release-status-released", app_js)
        self.assertIn("release-status release-status-planned", app_js)
        self.assertIn("release-status release-status-archived", app_js)
        self.assertIn("release-status release-status-overdue", app_js)
        self.assertIn('<span class="${getReleaseStatusClass(row.status)}">', app_js)
        self.assertIn("const statusClass = getReleaseStatusClass(rawStatus)", app_js)
        self.assertIn('<span class="${statusClass}">${statusLabel}</span>', app_js)
        self.assertIn(".release-status-released", style_css)
        self.assertIn(".release-status-planned", style_css)
        self.assertIn(".release-status-archived", style_css)
        self.assertIn(".release-status-overdue", style_css)

    def test_infocomm_schedule_panel_renders_dates_only(self) -> None:
        app_js = Path("frontend/app.js").read_text(encoding="utf-8")

        self.assertIn("No schedule dates available.", app_js)
        self.assertIn("(state.infocomm.schedule || []).map((item) => item.date)", app_js)
        self.assertNotIn("session.duration", app_js)
        self.assertNotIn("session.location", app_js)
        self.assertNotIn("session.description", app_js)

    def test_teams_workspace_uses_live_search_and_member_details_panel(self) -> None:
        app_js = Path("frontend/app.js").read_text(encoding="utf-8")
        index_html = Path("frontend/index.html").read_text(encoding="utf-8")

        self.assertIn("teamWorkspaceSearchInput", app_js)
        self.assertIn("addEventListener(\"input\"", app_js)
        self.assertIn("No teams match your search.", app_js)
        self.assertIn("Select a team to view details and members.", app_js)
        self.assertIn("<h4>${escapeHtml(teamDisplayName)}</h4>", app_js)
        self.assertIn("Team Member Details", app_js)
        self.assertIn("Release Trend", app_js)
        self.assertIn('class="team-detail-panel"', app_js)
        self.assertIn("<th>Role</th>", app_js)
        self.assertIn("<th>Skillset</th>", app_js)
        self.assertIn("<th>Contractor</th>", app_js)
        self.assertIn("<th>Notes</th>", app_js)
        self.assertIn("teamDetailContent", index_html)
        self.assertNotIn("teamDetailTabs", index_html)


if __name__ == "__main__":
    unittest.main()
