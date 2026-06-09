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

        self.assertIn('tabName === "teams" || tabName === "infocomm"', app_js)
        self.assertIn("controlToolbar", app_js)
        self.assertIn('classList.remove("control-toolbar", "panel")', app_js)
        self.assertIn('classList.add("control-toolbar", "panel")', app_js)
        self.assertIn("el.controlToolbar.hidden = hideFilters", app_js)
        self.assertIn('apiGet("/api/teams")', app_js)

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
