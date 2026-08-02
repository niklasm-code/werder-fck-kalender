"""Verwaltet den bekannten Ticket-Vorverkaufsstatus für erreichbare Auswärtsspiele.

Dieses Skript recherchiert NICHT selbst im Web (Vereins-News-Seiten sind unstrukturierter
Freitext, kein sauber parsbares Format) - das übernimmt der wöchentliche Scheduled-Task-Lauf
per WebFetch/WebSearch (dort läuft ein echter Claude-Agent, der Freitext verstehen kann).
Dieses Skript ist die Zustandsverwaltung dazwischen:

  python ticket_watch.py list-open   -> JSON-Liste erreichbarer Auswärtsspiele ohne bekannten VVK-Termin
  python ticket_watch.py list-known  -> JSON-Liste bereits bekannter VVK-Termine
  python ticket_watch.py record <match_id> <sale_start_iso> <source_url>
                                      -> trägt einen recherchierten VVK-Termin ein
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from fixtures import get_relevant_matches
from reachable_cities import is_reachable_away, reachable_away_city

STATE_PATH = Path(__file__).parent / "state.json"


def load_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"known_ticket_sales": {}}


def save_state(state):
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def open_reachable_matches():
    """Erreichbare Auswärtsspiele, die noch in der Zukunft liegen und noch keinen bekannten VVK-Termin haben."""
    state = load_state()
    known = state.get("known_ticket_sales", {})
    now = datetime.now(timezone.utc).isoformat()

    open_matches = []
    for m in get_relevant_matches():
        if not is_reachable_away(m):
            continue
        if m["is_finished"]:
            continue
        if (m["kickoff"] or "") < now:
            continue
        match_id = str(m["match_id"])
        if match_id in known:
            continue
        open_matches.append({
            "match_id": m["match_id"],
            "competition": m["competition"],
            "city": reachable_away_city(m),
            "opponent_home_team": m["home_team_name"],
            "away_team_name": m["away_team_name"],
            "kickoff_local": m["kickoff_local"],
        })
    return open_matches


def known_ticket_sales():
    state = load_state()
    return state.get("known_ticket_sales", {})


def record_ticket_sale(match_id, sale_start_iso, source_url):
    state = load_state()
    state.setdefault("known_ticket_sales", {})[str(match_id)] = {
        "sale_start": sale_start_iso,
        "source_url": source_url,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    save_state(state)


def _print_json(data):
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    if command == "list-open":
        _print_json(open_reachable_matches())
    elif command == "list-known":
        _print_json(known_ticket_sales())
    elif command == "record":
        if len(sys.argv) != 5:
            print("Nutzung: python ticket_watch.py record <match_id> <sale_start_iso> <source_url>")
            sys.exit(1)
        _, _, match_id, sale_start_iso, source_url = sys.argv
        record_ticket_sale(match_id, sale_start_iso, source_url)
        print(f"Gespeichert: Match {match_id} -> Vorverkaufsstart {sale_start_iso}")
    else:
        print(f"Unbekannter Befehl: {command}")
        print(__doc__)
        sys.exit(1)
