"""User-friendly labels (Polish) for technical type strings.

Frontend can override; backend exposes via /api/labels too.
"""
from __future__ import annotations

EVENT_TYPE_LABELS: dict[str, str] = {
    "youtube_watch": "Obejrzany film na YouTube",
    "youtube_search": "Wyszukiwanie na YouTube",
    "youtube_subscribe": "Subskrypcja na YouTube",
    "youtube_comment": "Komentarz na YouTube",
    "chrome_visit": "Odwiedzona strona",
    "chrome_bookmark": "Zakładka Chrome",
    "my_activity": "Aktywność Google",
    "search_query": "Wyszukiwanie Google",
    "location_point": "Punkt lokalizacji",
    "calendar_event": "Wydarzenie w kalendarzu",
    "contact": "Kontakt",
    "mail_message": "E-mail",
    "drive_activity": "Aktywność w Google Drive",
    "maps_place": "Miejsce w Mapach Google",
    "play_install": "Instalacja z Google Play",
    "assistant_activity": "Aktywność Asystenta Google",
    "fit_activity": "Aktywność w Google Fit",
    "keep_note": "Notatka Google Keep",
    "task": "Zadanie Google",
    "ads_activity": "Aktywność reklamowa",
    "task": "Zadanie Google Tasks",
    "meet_conference": "Spotkanie Google Meet",
    "gemini_activity": "Konwersacja Gemini",
    "mail_signature": "Sygnatura Gmail",
    "mail_vacation": "Autoresponder Gmail",
    "mail_blocked_address": "Zablokowany adres Gmail",
    "mail_delegate": "Delegat Gmail",
    "drive_file": "Plik na Google Drive",
    "unknown": "Inne zdarzenie",
}

SOURCE_LABELS: dict[str, str] = {
    "youtube": "YouTube",
    "chrome": "Chrome",
    "my_activity": "Moja aktywność",
    "location": "Historia lokalizacji",
    "calendar": "Kalendarz",
    "contacts": "Kontakty",
    "mail": "Poczta",
    "drive": "Drive",
    "maps": "Mapy",
    "play": "Play Store",
    "assistant": "Asystent",
    "fit": "Fit",
    "keep": "Keep",
    "tasks": "Zadania",
    "ads": "Reklamy",
    "search": "Wyszukiwarka",
    "meet": "Google Meet",
    "gemini": "Gemini",
    "drive": "Google Drive",
    "unknown": "Inne",
}


def label_for_type(t: str | None) -> str:
    if not t:
        return EVENT_TYPE_LABELS["unknown"]
    return EVENT_TYPE_LABELS.get(t, t)


def label_for_source(s: str | None) -> str:
    if not s:
        return SOURCE_LABELS["unknown"]
    return SOURCE_LABELS.get(s, s)
