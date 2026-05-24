"""server.py — mcp-calendar MCP server entry point.

Google Calendar integration using OAuth refresh token flow.
List, create, update, delete events. Find free/busy slots.

Setup: see README for OAuth flow to get a refresh token.
"""

import httpx
from datetime import datetime, timedelta, timezone
from typing import Any
from mcp.server.fastmcp import FastMCP
from src.config import settings

mcp = FastMCP(
    "mcp-calendar",
    instructions="Google Calendar MCP for mmiri28 solutions. List, create, update, delete events. Find free slots for scheduling.",
)


def _access_token() -> str:
    """Exchange refresh token for a fresh access token."""
    r = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": settings.client_id,
            "client_secret": settings.client_secret,
            "refresh_token": settings.refresh_token,
            "grant_type": "refresh_token",
        }, timeout=10,
    )
    data = r.json()
    if r.status_code != 200:
        raise RuntimeError(f"Token refresh failed: {data.get('error_description', data)}")
    return data["access_token"]


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_access_token()}",
            "Content-Type": "application/json"}


@mcp.tool()
def health_check() -> dict:
    """Verify Google OAuth credentials work."""
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        token = _access_token()
        return {"ok": True, "status": "connected",
                "token_obtained": bool(token),
                "default_calendar": settings.default_calendar}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def list_calendars() -> dict:
    """List all calendars the authorised user has access to."""
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        r = httpx.get(f"{settings.base_url}/users/me/calendarList",
                      headers=_headers(), timeout=15)
        if r.status_code != 200:
            return {"ok": False, "error": r.json().get("error", {}).get("message")}
        cals = [{"id": c["id"], "summary": c["summary"],
                 "primary": c.get("primary", False),
                 "access_role": c.get("accessRole")}
                for c in r.json().get("items", [])]
        return {"ok": True, "count": len(cals), "calendars": cals}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def list_events(
    calendar_id: str | None = None,
    days_ahead: int = 7,
    max_results: int = 20,
) -> dict[str, Any]:
    """
    List upcoming events from a calendar.

    Args:
        calendar_id: Calendar ID. Default: primary.
        days_ahead:  Look ahead this many days. Default: 7.
        max_results: Max events. Default: 20.
    """
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    cal = calendar_id or settings.default_calendar
    now = datetime.now(timezone.utc)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=days_ahead)).isoformat()

    try:
        r = httpx.get(
            f"{settings.base_url}/calendars/{cal}/events",
            headers=_headers(),
            params={"timeMin": time_min, "timeMax": time_max,
                    "maxResults": max_results, "singleEvents": "true",
                    "orderBy": "startTime"},
            timeout=15,
        )
        if r.status_code != 200:
            return {"ok": False, "error": r.json().get("error", {}).get("message")}

        events = []
        for e in r.json().get("items", []):
            start = e.get("start", {})
            end = e.get("end", {})
            events.append({
                "id": e["id"],
                "summary": e.get("summary", "(no title)"),
                "start": start.get("dateTime") or start.get("date"),
                "end": end.get("dateTime") or end.get("date"),
                "location": e.get("location"),
                "attendees": [a.get("email") for a in e.get("attendees", [])],
                "html_link": e.get("htmlLink"),
            })
        return {"ok": True, "calendar": cal, "count": len(events), "events": events}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def create_event(
    summary: str,
    start_time: str,
    end_time: str,
    description: str = "",
    location: str = "",
    attendees: list[str] | None = None,
    calendar_id: str | None = None,
    send_invites: bool = False,
) -> dict[str, Any]:
    """
    Create a calendar event.

    Args:
        summary:      Event title.
        start_time:   ISO 8601 datetime (e.g. "2026-06-01T14:00:00+01:00").
        end_time:     ISO 8601 datetime.
        description:  Event description.
        location:     Physical or virtual location.
        attendees:    List of email addresses.
        calendar_id:  Calendar to create in. Default: primary.
        send_invites: Email invites to attendees.
    """
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    cal = calendar_id or settings.default_calendar
    body = {
        "summary": summary,
        "description": description,
        "location": location,
        "start": {"dateTime": start_time},
        "end": {"dateTime": end_time},
    }
    if attendees:
        body["attendees"] = [{"email": e} for e in attendees]

    try:
        r = httpx.post(
            f"{settings.base_url}/calendars/{cal}/events",
            headers=_headers(), json=body,
            params={"sendUpdates": "all" if send_invites else "none"},
            timeout=15,
        )
        if r.status_code in (200, 201):
            data = r.json()
            return {"ok": True, "event_id": data["id"],
                    "html_link": data.get("htmlLink"),
                    "summary": summary, "start": start_time}
        return {"ok": False, "error": r.json().get("error", {}).get("message")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def delete_event(event_id: str, calendar_id: str | None = None) -> dict:
    """Delete an event."""
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    cal = calendar_id or settings.default_calendar
    try:
        r = httpx.delete(
            f"{settings.base_url}/calendars/{cal}/events/{event_id}",
            headers=_headers(), timeout=10,
        )
        if r.status_code in (200, 204):
            return {"ok": True, "deleted": True, "event_id": event_id}
        return {"ok": False, "error": f"HTTP {r.status_code}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def find_free_slot(
    duration_minutes: int = 60,
    days_ahead: int = 7,
    working_hours_start: int = 9,
    working_hours_end: int = 17,
    calendar_ids: list[str] | None = None,
) -> dict[str, Any]:
    """
    Find available time slots across one or more calendars.

    Args:
        duration_minutes:    Slot duration needed.
        days_ahead:          How far ahead to search.
        working_hours_start: Earliest hour (24h).
        working_hours_end:   Latest hour (24h).
        calendar_ids:        Calendars to check. Default: primary.
    """
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    cals = calendar_ids or [settings.default_calendar]
    now = datetime.now(timezone.utc)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=days_ahead)).isoformat()

    try:
        r = httpx.post(
            f"{settings.base_url}/freeBusy",
            headers=_headers(),
            json={"timeMin": time_min, "timeMax": time_max,
                  "items": [{"id": c} for c in cals]},
            timeout=15,
        )
        if r.status_code != 200:
            return {"ok": False, "error": r.json().get("error", {}).get("message")}

        # Merge busy times across all calendars
        busy = []
        for cal_id, info in r.json().get("calendars", {}).items():
            for b in info.get("busy", []):
                busy.append((datetime.fromisoformat(b["start"].replace("Z", "+00:00")),
                             datetime.fromisoformat(b["end"].replace("Z", "+00:00"))))
        busy.sort()

        # Find gaps within working hours
        slots = []
        cursor = now
        end_search = now + timedelta(days=days_ahead)
        duration = timedelta(minutes=duration_minutes)

        while cursor < end_search and len(slots) < 10:
            # Skip to working hours
            if cursor.hour < working_hours_start:
                cursor = cursor.replace(hour=working_hours_start, minute=0, second=0, microsecond=0)
            if cursor.hour >= working_hours_end:
                cursor = (cursor + timedelta(days=1)).replace(hour=working_hours_start, minute=0, second=0, microsecond=0)
                continue
            # Skip weekends
            if cursor.weekday() >= 5:
                cursor = (cursor + timedelta(days=1)).replace(hour=working_hours_start, minute=0, second=0, microsecond=0)
                continue

            slot_end = cursor + duration
            if slot_end.hour > working_hours_end or slot_end.day != cursor.day:
                cursor = (cursor + timedelta(days=1)).replace(hour=working_hours_start, minute=0, second=0, microsecond=0)
                continue

            # Check if slot conflicts with busy times
            conflict = False
            for b_start, b_end in busy:
                if cursor < b_end and slot_end > b_start:
                    conflict = True
                    cursor = b_end
                    break

            if not conflict:
                slots.append({"start": cursor.isoformat(), "end": slot_end.isoformat()})
                cursor = slot_end + timedelta(minutes=15)

        return {"ok": True, "duration_minutes": duration_minutes,
                "slot_count": len(slots), "slots": slots}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
