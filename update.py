"""Orchestriert einen kompletten Update-Lauf: Spielplan neu abrufen, kalender.ics neu bauen,
und (falls das Verzeichnis ein Git-Repo mit Remote ist) committen + pushen.

Die Ticket-Recherche (WebFetch/WebSearch auf fck.de/werder.de) läuft NICHT hier, sondern im
aufrufenden Scheduled-Task-Prompt, der vor diesem Skript `ticket_watch.py list-open` und
danach `ticket_watch.py record ...` für neu gefundene Termine aufruft. Dieses Skript baut nur
aus dem aktuellen state.json den finalen Kalender und veröffentlicht ihn.
"""
import subprocess
import sys
from pathlib import Path

from fixtures import get_relevant_matches
from generate_ics import generate_calendar, ICS_PATH
from reachable_cities import is_reachable_away

REPO_DIR = Path(__file__).parent


def _run(cmd):
    return subprocess.run(cmd, cwd=REPO_DIR, capture_output=True, text=True)


def is_git_repo_with_remote():
    result = _run(["git", "rev-parse", "--is-inside-work-tree"])
    if result.returncode != 0:
        return False
    remotes = _run(["git", "remote"])
    return bool(remotes.stdout.strip())


def git_commit_and_push():
    _run(["git", "add", "kalender.ics", "state.json"])
    status = _run(["git", "status", "--porcelain"])
    if not status.stdout.strip():
        print("Keine Änderungen am Kalender - kein neuer Commit nötig.")
        return
    commit = _run(["git", "commit", "-m", "Update Spielplan/Ticket-Kalender"])
    print(commit.stdout.strip())
    if commit.returncode != 0:
        print(commit.stderr.strip())
        return
    push = _run(["git", "push"])
    print(push.stdout.strip())
    if push.returncode != 0:
        print(push.stderr.strip())


def main():
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    matches = get_relevant_matches()
    reachable = [m for m in matches if is_reachable_away(m)]
    print(f"{len(matches)} Pflichtspiele, davon {len(reachable)} erreichbare Auswärtsspiele.")

    ics_content = generate_calendar()
    ICS_PATH.write_text(ics_content, encoding="utf-8", newline="")
    print(f"kalender.ics geschrieben ({ics_content.count('BEGIN:VEVENT')} Events).")

    if is_git_repo_with_remote():
        git_commit_and_push()
    else:
        print("Kein Git-Repo mit Remote gefunden - kalender.ics wurde nur lokal aktualisiert, kein Push.")


if __name__ == "__main__":
    main()
