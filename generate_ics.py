"""Baut kalender.ics aus den Pflichtspielen und bekannten Ticket-Vorverkaufsterminen.

UIDs sind stabil (an die OpenLigaDB matchID gekoppelt), damit ein erneuter Lauf bestehende
Events in Outlook aktualisiert statt zu duplizieren.
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fixtures import get_relevant_matches, WERDER_TEAM_ID, KAISERSLAUTERN_TEAM_ID
from reachable_cities import is_reachable_away, reachable_away_city
from ticket_watch import known_ticket_sales

ICS_PATH = Path(__file__).parent / "kalender.ics"
UID_DOMAIN = "werder-fck-kalender.local"
MATCH_DURATION = timedelta(hours=2)


def _fold(line):
    """RFC5545 Zeilenumbruch: max. 75 Oktette pro Zeile, Folgezeilen mit einem Leerzeichen eingerückt."""
    encoded = line.encode("utf-8")
    if len(encoded) <= 75:
        return line
    parts = []
    while len(encoded) > 75:
        cut = 75
        # nicht mitten in einem UTF-8-Mehrbyte-Zeichen trennen
        while (encoded[cut] & 0xC0) == 0x80:
            cut -= 1
        parts.append(encoded[:cut].decode("utf-8"))
        encoded = encoded[cut:]
    parts.append(encoded.decode("utf-8"))
    return ("\r\n ").join(parts)


def _escape(text):
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _to_ics_utc(iso_str):
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _now_ics_utc():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _team_label(match):
    return "Werder Bremen" if WERDER_TEAM_ID in (match["home_team_id"], match["away_team_id"]) else "1. FC Kaiserslautern"


def build_match_event(match):
    lines = ["BEGIN:VEVENT"]
    lines.append(f"UID:match-{match['match_id']}@{UID_DOMAIN}")
    lines.append(f"DTSTAMP:{_now_ics_utc()}")
    lines.append(f"DTSTART:{_to_ics_utc(match['kickoff'])}")
    end_dt = datetime.fromisoformat(match["kickoff"].replace("Z", "+00:00")).astimezone(timezone.utc) + MATCH_DURATION
    lines.append(f"DTEND:{end_dt.strftime('%Y%m%dT%H%M%SZ')}")

    city = reachable_away_city(match)
    summary = f"{match['home_team_name']} vs {match['away_team_name']}"
    if is_reachable_away(match):
        summary = f"\U0001F3AB AUSWÄRTS ({city}): {summary}"
    lines.append(f"SUMMARY:{_escape(summary)}")

    description = f"{match['competition']} - {_team_label(match)}"
    if is_reachable_away(match):
        description += f"\\nErreichbares Auswärtsspiel in {city} - an Ticketbewerbung denken!"
    lines.append(f"DESCRIPTION:{description}")
    lines.append("CATEGORIES:Fussball")

    lines.append("BEGIN:VALARM")
    lines.append("ACTION:DISPLAY")
    lines.append(f"DESCRIPTION:{_escape(summary)}")
    lines.append("TRIGGER:-PT1H")
    lines.append("END:VALARM")

    lines.append("END:VEVENT")
    return [_fold(l) for l in lines]


def build_ticket_event(match, sale_info):
    sale_start_iso = sale_info["sale_start"]
    source_url = sale_info.get("source_url", "")
    city = reachable_away_city(match)
    summary = f"\U0001F3AB Ticketverkauf startet: {match['home_team_name']} vs {match['away_team_name']}"

    lines = ["BEGIN:VEVENT"]
    lines.append(f"UID:ticket-{match['match_id']}@{UID_DOMAIN}")
    lines.append(f"DTSTAMP:{_now_ics_utc()}")
    lines.append(f"DTSTART:{_to_ics_utc(sale_start_iso)}")
    end_dt = datetime.fromisoformat(sale_start_iso.replace("Z", "+00:00")).astimezone(timezone.utc) + timedelta(hours=1)
    lines.append(f"DTEND:{end_dt.strftime('%Y%m%dT%H%M%SZ')}")
    lines.append(f"SUMMARY:{_escape(summary)}")
    description = f"Ticket-Bewerbung fuer erreichbares Auswaertsspiel in {city}."
    if source_url:
        description += f"\\nQuelle: {source_url}"
    lines.append(f"DESCRIPTION:{description}")
    lines.append("CATEGORIES:Fussball,Tickets")

    lines.append("BEGIN:VALARM")
    lines.append("ACTION:DISPLAY")
    lines.append(f"DESCRIPTION:{_escape(summary)}")
    lines.append("TRIGGER:-P1D")
    lines.append("END:VALARM")

    lines.append("END:VEVENT")
    return [_fold(l) for l in lines]


def generate_calendar():
    matches = get_relevant_matches()
    sales = known_ticket_sales()

    body = []
    for m in matches:
        if not m["kickoff"]:
            continue
        body.extend(build_match_event(m))
        match_id = str(m["match_id"])
        if is_reachable_away(m) and match_id in sales:
            body.extend(build_ticket_event(m, sales[match_id]))

    calendar_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//werder-fck-kalender//Saison 2026-27//DE",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Werder Bremen & 1. FC Kaiserslautern 2026-27",
        "X-WR-TIMEZONE:UTC",
        *body,
        "END:VCALENDAR",
    ]
    return "\r\n".join(calendar_lines) + "\r\n"


if __name__ == "__main__":
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    ics_content = generate_calendar()
    ICS_PATH.write_text(ics_content, encoding="utf-8", newline="")
    event_count = ics_content.count("BEGIN:VEVENT")
    print(f"{event_count} Events geschrieben nach {ICS_PATH}")
