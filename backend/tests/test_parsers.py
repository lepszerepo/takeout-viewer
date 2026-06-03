from pathlib import Path
from app.importer.parsers.youtube import watch_parser
from app.importer.parsers.my_activity import activity_parser

FIXTURES = Path(__file__).parent / "fixtures"


def test_youtube_watch_json():
    events = list(watch_parser(FIXTURES / "watch-history.json", "watch-history.json"))
    assert len(events) == 2
    assert events[0].source == "youtube"
    assert events[0].type == "youtube_watch"
    assert events[0].title == "Test Video A"
    assert events[0].url and "AAAAAAAAAAA" in events[0].url
    assert events[0].timestamp is not None


def test_my_activity_classification():
    events = list(activity_parser(FIXTURES / "my-activity-search.json", "my-activity-search.json"))
    sources = [e.source for e in events]
    assert "search" in sources
    assert "chrome" in sources
    chrome = next(e for e in events if e.source == "chrome")
    assert chrome.type == "chrome_visit"
    search = next(e for e in events if e.source == "search")
    assert search.type == "search_query"


def test_event_hash_is_stable():
    events = list(watch_parser(FIXTURES / "watch-history.json", "watch-history.json"))
    h1 = events[0].compute_hash()
    h2 = events[0].compute_hash()
    assert h1 == h2
    assert h1 != events[1].compute_hash()
