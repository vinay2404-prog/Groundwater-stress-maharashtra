"""Page-level smoke tests that run against a *fresh* Streamlit session.

The full sweep visits the pages in order, which can hide bugs that only
appear when a page is opened before anything else has run: session state
written by one page is then already present for the next. These tests open a
fresh app for every page so that order cannot hide a problem.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from streamlit.testing.v1 import AppTest

APP_FILE = str(Path(__file__).resolve().parents[1] / "app.py")

# Pages that must work on a cold start, with nothing in session state.
COLD_START_PAGES = [
    "Data & Reports",
    "Data & Reports",
    "AI Assistant",
    "State Dashboard",
    "Data & Reports",
]


def _open(page: str) -> AppTest:
    at = AppTest.from_file(APP_FILE, default_timeout=300)
    at.run()
    at.sidebar.radio[0].set_value(page)
    at.run()
    return at


@pytest.mark.parametrize("page", COLD_START_PAGES)
def test_page_opens_on_a_fresh_session(page):
    at = _open(page)
    assert not at.exception, f"{page} raised: {[str(e.value) for e in at.exception]}"


def test_query_history_on_a_fresh_session_shows_the_empty_state():
    at = _open("Data & Reports")
    assert not at.exception
    assert any("No query history yet" in info.value for info in at.info)


def test_chatbot_uses_its_own_greeting():
    """The chat page must not inherit a stale greeting from elsewhere."""
    at = _open("AI Assistant")
    assert not at.exception
    text = "\n".join(markdown.value for markdown in at.markdown)
    assert "groundwater intelligence assistant" in text.lower()
    assert "ask me anything about your groundwater data" not in text.lower()


def test_clear_history_button_works_on_a_fresh_session():
    at = _open("Data & Reports")
    assert not at.exception
    at.button[0].click()
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
