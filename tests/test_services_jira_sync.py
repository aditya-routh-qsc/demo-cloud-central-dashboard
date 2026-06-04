from __future__ import annotations

import sqlite3
import unittest
from unittest.mock import patch

import requests

import services


class _MockResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self) -> dict:
        return self._payload


class JiraTeamsSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = sqlite3.connect(":memory:")

    def tearDown(self) -> None:
        self.conn.close()

    def _success_payload(self) -> dict:
        return {
            "data": {
                "team": {
                    "teamSearchV2": {
                        "nodes": [
                            {
                                "teamId": "team-1",
                                "displayName": "Platform Team",
                                "description": "Owns shared cloud platform",
                                "members": {
                                    "nodes": [
                                        {
                                            "accountId": "acc-1",
                                            "displayName": "Ada Lovelace",
                                            "email": "ada@example.com",
                                        },
                                        {
                                            "accountId": "acc-2",
                                            "displayName": "Grace Hopper",
                                            "email": "grace@example.com",
                                        },
                                    ]
                                },
                            }
                        ]
                    }
                }
            }
        }

    def test_enrich_teams_data_with_profile_urls(self) -> None:
        payload = self._success_payload()

        enriched = services._enrich_teams_data_with_profile_urls(
            payload,
            "example.atlassian.net",
        )

        member = enriched["data"]["team"]["teamSearchV2"]["nodes"][0]["members"]["nodes"][0]
        self.assertEqual(
            member["profile_url"],
            "https://example.atlassian.net/jira/people/acc-1",
        )

    @patch("services.sqlite3.connect")
    @patch("services.requests.post")
    def test_sync_pipeline_successful_ingestion(self, mock_post, mock_connect) -> None:
        mock_connect.return_value = self.conn
        mock_post.return_value = _MockResponse(self._success_payload(), status_code=200)

        result = services.sync_jira_teams_pipeline(
            domain="example.atlassian.net",
            email="user@example.com",
            api_token="token",
            cloud_id="cloud-123",
            tql_query="displayName ~ \"Platform\"",
            db_path=":memory:",
        )

        team_count = self.conn.execute("SELECT COUNT(*) FROM teams").fetchone()[0]
        member_count = self.conn.execute("SELECT COUNT(*) FROM team_members").fetchone()[0]

        self.assertEqual(result["teams_upserted"], 1)
        self.assertEqual(result["members_upserted"], 2)
        self.assertEqual(team_count, 1)
        self.assertEqual(member_count, 2)

        stored_profile_url = self.conn.execute(
            "SELECT profile_url FROM team_members WHERE team_id = ? AND account_id = ?",
            ("team-1", "acc-1"),
        ).fetchone()[0]
        self.assertEqual(stored_profile_url, "https://example.atlassian.net/jira/people/acc-1")

    @patch("services.sqlite3.connect")
    def test_save_jira_data_to_db_persists_raw_json_fields(self, mock_connect) -> None:
        mock_connect.return_value = self.conn
        services.init_jira_tables(":memory:")

        payload = {
            "data": {
                "team": {
                    "teamSearchV2": {
                        "nodes": [
                            {
                                "team": {
                                    "id": "team-ari-1",
                                    "displayName": "Cloud Ops",
                                    "description": "Operations team",
                                    "organizationId": "org-1",
                                    "state": "ACTIVE",
                                    "type": "DEFAULT",
                                    "isVerified": True,
                                    "profileUrl": "https://example.atlassian.net/wiki/spaces/TEAM",
                                    "members": {
                                        "nodes": [
                                            {
                                                "member": {
                                                    "accountId": "acc-raw-1",
                                                    "canonicalAccountId": "canon-1",
                                                    "name": "Raw Member",
                                                    "email": "raw@example.com",
                                                    "accountStatus": "active",
                                                    "nickname": "raw",
                                                    "picture": "https://example/avatar.png",
                                                    "zoneinfo": "UTC",
                                                    "locale": "en_US",
                                                    "orgId": "org-1",
                                                    "profile_url": "https://example.atlassian.net/jira/people/acc-raw-1",
                                                },
                                                "role": "MEMBER",
                                                "state": "ACTIVE",
                                            }
                                        ]
                                    },
                                },
                                "memberCount": 1,
                                "includesYou": True,
                            }
                        ]
                    }
                }
            }
        }

        services.save_jira_data_to_db(":memory:", payload, "cloud-123")

        team_row = self.conn.execute(
            "SELECT team_json, member_count, includes_you FROM teams WHERE team_id = ?",
            ("team-ari-1",),
        ).fetchone()
        member_row = self.conn.execute(
            "SELECT member_json, member_role, member_state, canonical_account_id FROM team_members WHERE team_id = ? AND account_id = ?",
            ("team-ari-1", "acc-raw-1"),
        ).fetchone()

        self.assertIsNotNone(team_row)
        self.assertIsNotNone(member_row)
        self.assertIn("Cloud Ops", str(team_row[0]))
        self.assertEqual(team_row[1], 1)
        self.assertEqual(team_row[2], 1)
        self.assertIn("Raw Member", str(member_row[0]))
        self.assertEqual(member_row[1], "MEMBER")
        self.assertEqual(member_row[2], "ACTIVE")
        self.assertEqual(member_row[3], "canon-1")

    @patch("services.sqlite3.connect")
    def test_save_jira_data_to_db_upsert_prevents_duplicates(self, mock_connect) -> None:
        mock_connect.return_value = self.conn
        services.init_jira_tables(":memory:")

        first_payload = self._success_payload()
        second_payload = self._success_payload()
        second_payload["data"]["team"]["teamSearchV2"]["nodes"][0]["displayName"] = "Platform Engineering"
        second_payload["data"]["team"]["teamSearchV2"]["nodes"][0]["members"]["nodes"][0]["email"] = "ada.new@example.com"

        services.save_jira_data_to_db(":memory:", first_payload, "cloud-123")
        services.save_jira_data_to_db(":memory:", second_payload, "cloud-123")

        team_count = self.conn.execute("SELECT COUNT(*) FROM teams WHERE team_id = ?", ("team-1",)).fetchone()[0]
        member_count = self.conn.execute(
            "SELECT COUNT(*) FROM team_members WHERE team_id = ? AND account_id = ?",
            ("team-1", "acc-1"),
        ).fetchone()[0]
        updated_team_name = self.conn.execute(
            "SELECT display_name FROM teams WHERE team_id = ?",
            ("team-1",),
        ).fetchone()[0]
        updated_member_email = self.conn.execute(
            "SELECT email FROM team_members WHERE team_id = ? AND account_id = ?",
            ("team-1", "acc-1"),
        ).fetchone()[0]

        self.assertEqual(team_count, 1)
        self.assertEqual(member_count, 1)
        self.assertEqual(updated_team_name, "Platform Engineering")
        self.assertEqual(updated_member_email, "ada.new@example.com")

    @patch("services.requests.post")
    def test_fetch_jira_teams_and_members_http_errors(self, mock_post) -> None:
        for status_code in (404, 500):
            with self.subTest(status_code=status_code):
                mock_post.return_value = _MockResponse(payload={}, status_code=status_code)
                with self.assertRaises(requests.HTTPError):
                    services.fetch_jira_teams_and_members(
                        domain="example.atlassian.net",
                        email="user@example.com",
                        api_token="token",
                        cloud_id="cloud-123",
                        tql_query="displayName ~ \"Platform\"",
                    )

    @patch("services.requests.post")
    def test_fetch_jira_teams_and_members_malformed_payload(self, mock_post) -> None:
        mock_post.return_value = _MockResponse(payload={}, status_code=200)

        with self.assertRaises(ValueError):
            services.fetch_jira_teams_and_members(
                domain="example.atlassian.net",
                email="user@example.com",
                api_token="token",
                cloud_id="cloud-123",
                tql_query="displayName ~ \"Platform\"",
            )


if __name__ == "__main__":
    unittest.main()
