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
        self.assertIn('id="releaseDependsSelectedList"', index_html)
        self.assertIn('id="releaseDependsSuggestions"', index_html)
        self.assertIn('id="releaseCoreleasesSelectedList"', index_html)
        self.assertIn('id="releaseCoreleasesSuggestions"', index_html)
        self.assertIn('id="releaseEditToggleBtn"', index_html)
        self.assertIn('id="releaseApplyRelationshipsBtn"', index_html)
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
        self.assertIn(".release-table-filters", style_css)

    def test_release_relationship_json_persistence_and_reconciliation_are_present(self) -> None:
        app_js = Path("frontend/app.js").read_text(encoding="utf-8")

        self.assertIn("RELEASE_RELATIONSHIPS_STORAGE_KEY", app_js)
        self.assertIn("normalizeReleaseRelationshipMap", app_js)
        self.assertIn("saveReleaseRelationshipsToLocalJson", app_js)
        self.assertIn("loadReleaseRelationshipsFromLocalJson", app_js)
        self.assertIn("scrubReleaseRelationshipsAgainstRows", app_js)
        self.assertIn("co_releases", app_js)
        self.assertIn("depends_on", app_js)

    def test_release_graph_panel_and_status_filter_rendering_are_present(self) -> None:
        app_js = Path("frontend/app.js").read_text(encoding="utf-8")
        style_css = Path("frontend/style.css").read_text(encoding="utf-8")

        self.assertIn("renderReleaseGraph", app_js)
        self.assertIn("window.cytoscape", app_js)
        self.assertIn("buildReleaseCoReleaseGroups", app_js)
        self.assertIn("getReleaseGraphRenderableIds", app_js)
        self.assertIn("syncReleasePanelVisibility", app_js)
        self.assertIn("state.release.graph.statusFilter", app_js)
        self.assertIn("status-planned", app_js)
        self.assertIn("status-archived", app_js)
        self.assertIn("status-overdue", app_js)
        self.assertIn(".release-graph-panel", style_css)
        self.assertIn(".release-graph-canvas", style_css)

    def test_release_edit_mode_and_suggestion_pickers_are_present(self) -> None:
        app_js = Path("frontend/app.js").read_text(encoding="utf-8")
        style_css = Path("frontend/style.css").read_text(encoding="utf-8")

        self.assertIn("state.release.editMode", app_js)
        self.assertIn("toggleSuggestionSelection", app_js)
        self.assertIn("buildReleaseSuggestionItems", app_js)
        self.assertIn("buildReleaseSelectedItems", app_js)
        self.assertIn("renderReleaseSelectedList", app_js)
        self.assertIn("renderReleaseSuggestionList", app_js)
        self.assertIn("Exit Edit", app_js)
        self.assertIn("Edit: Off", app_js)
        self.assertIn(".release-selected-list", style_css)
        self.assertIn(".release-suggestions", style_css)
        self.assertIn(".release-suggestion-item", style_css)

    def test_release_status_cells_have_theme_aligned_color_classes(self) -> None:
        app_js = Path("frontend/app.js").read_text(encoding="utf-8")
        style_css = Path("frontend/style.css").read_text(encoding="utf-8")

        self.assertIn("getReleaseStatusClass", app_js)
        self.assertIn("release-status release-status-released", app_js)
        self.assertIn("release-status release-status-planned", app_js)
        self.assertIn("release-status release-status-archived", app_js)
        self.assertIn("release-status release-status-overdue", app_js)
        self.assertIn('<span class="${getReleaseStatusClass(row.status)}">', app_js)
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
        self.assertIn("<th>Role</th>", app_js)
        self.assertIn("<th>Skillset</th>", app_js)
        self.assertIn("<th>Contractor</th>", app_js)
        self.assertIn("<th>Notes</th>", app_js)
        self.assertIn("teamDetailContent", index_html)
        self.assertNotIn("teamDetailTabs", index_html)


if __name__ == "__main__":
    unittest.main()
