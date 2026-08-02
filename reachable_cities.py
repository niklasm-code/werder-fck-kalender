"""Erkennt Auswärtsspiele von Werder Bremen / 1. FC Kaiserslautern bei einem der 6 von München aus
erreichbaren Vereine (Stuttgart, Nürnberg, Fürth, Heidenheim, Augsburg, München).

Alle Team-IDs wurden über https://api.openligadb.de/getavailableteams/<liga>/2026 verifiziert.
"""
from fixtures import WERDER_TEAM_ID, KAISERSLAUTERN_TEAM_ID

SUPPORTED_TEAM_IDS = {WERDER_TEAM_ID, KAISERSLAUTERN_TEAM_ID}

# teamId -> Anzeigename der Stadt
REACHABLE_CITY_TEAM_IDS = {
    16: "Stuttgart",        # VfB Stuttgart (Bundesliga)
    79: "Nürnberg",         # 1. FC Nürnberg (2. Bundesliga)
    115: "Fürth",           # SpVgg Greuther Fürth (2. Bundesliga)
    199: "Heidenheim",      # 1. FC Heidenheim 1846 (2. Bundesliga)
    95: "Augsburg",         # FC Augsburg (Bundesliga)
    40: "München",          # FC Bayern München (Bundesliga)
}

# Fallback für den DFB-Pokal: dort kann per Auslosung auch ein Verein aus München
# auftauchen, dessen teamId oben nicht hinterlegt ist (z.B. TSV 1860 München aus der
# 3. Liga). Da Pokal-Gegner aus unteren Ligen nicht vorab bekannt sind, wird zusätzlich
# der Vereinsname auf "München" geprüft.
REACHABLE_CITY_NAME_HINTS = {
    "münchen": "München",
    "muenchen": "München",
}


def reachable_city_for_team(team_id, team_name):
    if team_id in REACHABLE_CITY_TEAM_IDS:
        return REACHABLE_CITY_TEAM_IDS[team_id]
    lower_name = team_name.lower()
    for hint, city in REACHABLE_CITY_NAME_HINTS.items():
        if hint in lower_name:
            return city
    return None


def is_reachable_away(match):
    """True, wenn Werder oder Kaiserslautern auswärts bei einem der 6 Reachable-Cities-Vereine spielt."""
    if match["away_team_id"] not in SUPPORTED_TEAM_IDS:
        return False
    return reachable_city_for_team(match["home_team_id"], match["home_team_name"]) is not None


def reachable_away_city(match):
    """Liefert den Stadtnamen, falls is_reachable_away(match) True ist, sonst None."""
    if not is_reachable_away(match):
        return None
    return reachable_city_for_team(match["home_team_id"], match["home_team_name"])


if __name__ == "__main__":
    from fixtures import get_relevant_matches
    import sys
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    matches = get_relevant_matches()
    reachable = [m for m in matches if is_reachable_away(m)]
    print(f"{len(reachable)} erreichbare Auswärtsspiele gefunden:\n")
    for m in reachable:
        city = reachable_away_city(m)
        print(f"[{m['competition']:12s}] {m['kickoff_local']:20s} {m['home_team_name']:30s} vs {m['away_team_name']:30s} -> {city}")
