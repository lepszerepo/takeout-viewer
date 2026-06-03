from datetime import datetime
from app.importer.dedupe import stable_hash


def test_stable_hash_same_inputs_same_output():
    ts = datetime(2024, 1, 1, 12, 0, 0)
    a = stable_hash("youtube", "youtube_watch", ts, "Title", "https://x")
    b = stable_hash("youtube", "youtube_watch", ts, "Title", "https://x")
    assert a == b


def test_stable_hash_changes_when_url_differs():
    ts = datetime(2024, 1, 1, 12, 0, 0)
    a = stable_hash("youtube", "youtube_watch", ts, "Title", "https://x")
    b = stable_hash("youtube", "youtube_watch", ts, "Title", "https://y")
    assert a != b


def test_stable_hash_no_timestamp_uses_raw_path():
    a = stable_hash("youtube", "youtube_watch", None, "Title", "https://x", raw_path="file1.json")
    b = stable_hash("youtube", "youtube_watch", None, "Title", "https://x", raw_path="file2.json")
    assert a != b


def test_stable_hash_microsecond_ignored():
    a = stable_hash(
        "x", "t", datetime(2024, 1, 1, 12, 0, 0, 1), "T", "u",
    )
    b = stable_hash(
        "x", "t", datetime(2024, 1, 1, 12, 0, 0, 999), "T", "u",
    )
    # microseconds are stripped → same hash
    assert a == b
