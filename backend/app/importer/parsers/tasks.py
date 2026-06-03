"""Google Tasks parser. File format: JSON containing taskLists → items[] → tasks."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

from ..normalizer import NormalizedEvent
from .base import parse_iso


def tasks_parser(path: Path, rel: str) -> Iterator[NormalizedEvent]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return

    task_lists = data.get("items", []) if isinstance(data, dict) else []
    if not isinstance(task_lists, list):
        return

    for tl in task_lists:
        if not isinstance(tl, dict):
            continue
        list_title = tl.get("title") or "Tasks"
        for t in tl.get("items", []) or []:
            if not isinstance(t, dict):
                continue
            title = t.get("title") or "(zadanie bez tytułu)"
            notes = t.get("notes")
            status = t.get("status")
            ts = (
                parse_iso(t.get("created"))
                or parse_iso(t.get("updated"))
            )
            completed_ts = parse_iso(t.get("completed"))
            scheduled = None
            sched = t.get("scheduled_time")
            if isinstance(sched, list) and sched:
                first = sched[0]
                if isinstance(first, dict):
                    scheduled = parse_iso(first.get("start"))
            description_lines = [f"Lista: {list_title}", f"Status: {status or '?'}"]
            if completed_ts:
                description_lines.append(f"Ukończono: {completed_ts.isoformat()}")
            if notes:
                description_lines.append(notes)
            yield NormalizedEvent(
                source="tasks",
                service="Google Tasks",
                category="task",
                type="task",
                title=title,
                description="\n".join(description_lines),
                timestamp=ts,
                end_timestamp=completed_ts or scheduled,
                metadata={
                    "list": list_title,
                    "status": status,
                    "task_type": t.get("task_type"),
                    "scheduled": scheduled.isoformat() if scheduled else None,
                    "completed": completed_ts.isoformat() if completed_ts else None,
                },
                raw_path=f"{rel}#{t.get('id')}",
            )


def register_parsers(register) -> None:
    register("tasks", "task", tasks_parser)
