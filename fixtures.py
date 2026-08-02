"""Ruft Pflichtspiele von Werder Bremen und 1. FC Kaiserslautern für die Saison 2026/27 von OpenLigaDB ab."""
import sys
import requests

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "https://api.openligadb.de"

# OpenLigaDB teamId je Verein (verifiziert über getavailableteams/bl1|bl2/2026)
WERDER_TEAM_ID = 134
KAISERSLAUTERN_TEAM_ID = 76

# Ligen, die für die Saison 2026/27 relevant sind (leagueShortcut, season)
LEAGUES = [
    ("bl1", 2026),   # Bundesliga (Werder Bremen)
    ("bl2", 2026),   # 2. Bundesliga (1. FC Kaiserslautern)
    ("dfb", 2026),   # DFB-Pokal 2026/27 (beide Vereine möglich)
]

RELEVANT_TEAM_IDS = {WERDER_TEAM_ID, KAISERSLAUTERN_TEAM_ID}


def fetch_league_matches(shortcut, season):
    url = f"{BASE_URL}/getmatchdata/{shortcut}/{season}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def normalize_match(raw, competition):
    team1 = raw["team1"]
    team2 = raw["team2"]
    return {
        "match_id": raw["matchID"],
        "competition": competition,
        "kickoff": raw.get("matchDateTimeUTC") or raw.get("matchDateTime"),
        "kickoff_local": raw.get("matchDateTime"),
        "home_team_id": team1["teamId"],
        "home_team_name": team1["teamName"],
        "away_team_id": team2["teamId"],
        "away_team_name": team2["teamName"],
        "is_finished": raw.get("matchIsFinished", False),
    }


def get_relevant_matches():
    """Liefert alle Werder- und Kaiserslautern-Pflichtspiele der Saison 2026/27, dedupliziert nach match_id."""
    matches_by_id = {}
    for shortcut, season in LEAGUES:
        try:
            raw_matches = fetch_league_matches(shortcut, season)
        except requests.RequestException as exc:
            print(f"Warnung: Abruf {shortcut}/{season} fehlgeschlagen: {exc}")
            continue

        competition = {"bl1": "Bundesliga", "bl2": "2. Bundesliga", "dfb": "DFB-Pokal"}[shortcut]

        for raw in raw_matches:
            team1_id = raw["team1"]["teamId"]
            team2_id = raw["team2"]["teamId"]
            if team1_id not in RELEVANT_TEAM_IDS and team2_id not in RELEVANT_TEAM_IDS:
                continue
            match = normalize_match(raw, competition)
            matches_by_id[match["match_id"]] = match

    return sorted(matches_by_id.values(), key=lambda m: m["kickoff"] or "")


if __name__ == "__main__":
    matches = get_relevant_matches()
    print(f"{len(matches)} Pflichtspiele gefunden:\n")
    for m in matches:
        team = "Werder" if WERDER_TEAM_ID in (m["home_team_id"], m["away_team_id"]) else "Kaiserslautern"
        print(f"[{m['competition']:12s}] {m['kickoff_local']:20s} {m['home_team_name']:30s} vs {m['away_team_name']:30s} ({team})")
