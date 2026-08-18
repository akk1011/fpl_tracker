"""Unit tests for etl/historical/vaastav_client.py's CSV parsing/HTTP handling.

Uses a fake response instead of a real network call.
"""
from unittest.mock import MagicMock, patch

from etl.historical import vaastav_client


class FakeResponse:
    def __init__(self, status_code, content=b""):
        self.status_code = status_code
        self.content = content

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_fetch_csv_returns_none_on_404():
    with patch.object(vaastav_client._session, "get", return_value=FakeResponse(404)):
        result = vaastav_client.fetch_csv("2016-17", "nonexistent.csv")
    assert result is None


def test_fetch_csv_strips_whitespace_from_header():
    """id_dict.csv's real header has a leading space after each comma
    (confirmed by direct fetch this session) — must not leak into row keys."""
    csv_bytes = b"Understat_ID, FPL_ID, Understat_Name\n1250, 233, Mohamed Salah\n"
    with patch.object(vaastav_client._session, "get", return_value=FakeResponse(200, csv_bytes)):
        rows = vaastav_client.fetch_csv("2021-22", "id_dict.csv")

    assert rows == [{"Understat_ID": "1250", "FPL_ID": "233", "Understat_Name": "Mohamed Salah"}]


def test_fetch_csv_raises_on_non_404_error():
    with patch.object(vaastav_client._session, "get", return_value=FakeResponse(500)):
        try:
            vaastav_client.fetch_csv("2020-21", "players_raw.csv")
            assert False, "expected an exception"
        except RuntimeError:
            pass


def test_fetch_understat_team_file_uses_correct_path():
    with patch.object(vaastav_client, "fetch_csv") as mock_fetch:
        vaastav_client.fetch_understat_team_file("2020-21", "Manchester_United")
    mock_fetch.assert_called_once_with("2020-21", "understat/understat_Manchester_United.csv")
