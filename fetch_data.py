#!/usr/bin/env python3
"""
PLC Fantasy Football Data Fetcher
Pulls standings + schedule from ESPN API and writes JSON files to data/.
Run this script whenever you want to refresh the site data, then commit and push.
"""

import requests
import json
import os

LEAGUE_ID = 365700
SEASON    = 2025
BASE      = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{SEASON}/segments/0/leagues/{LEAGUE_ID}"

COOKIES = {
    "espn_s2": "AEBfjJ2szeOszntWJEB6ZyJRSpbISmH1TpiEiuurFWZ2TAtAsHc6pbgEHjg29MUXgySloxyluKVCl3cj3INtCKMfj9e6khvWdhFE3VqO9ZbH4pGk4I%2BVrp7CrWRKaMlDV%2BzO09dBFfJDjo22LvQggpjZ8BMOQJt%2BLI%2FO47mJR4ODcrmiWQOcUmk4qATrBKP2VLCDSWjiPZJeVvo2to%2F5dMubn7n%2FL7Coy2wNf%2BEEbRmsB86glraNOlNpxdITAEUwafHZR1Rk4RpTqBmae4JnILw6D4TIXnojcdvEtpT%2Fv2%2F8Ub2s4ASZzw5xZNp2H85eqoY%3D",
    "SWID": "{CDCCE86E-74FE-4C8E-9570-8FA7118D6BDF}",
}
HEADERS = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}

REGULAR_SEASON_WEEKS = 14


def fetch(view):
    r = requests.get(BASE, params={"view": view}, cookies=COOKIES, headers=HEADERS)
    r.raise_for_status()
    return r.json()


def calc_streak(team_id, schedule):
    """Return streak string like 'W3' or 'L2' based on end of regular season."""
    results = []
    for week in range(1, REGULAR_SEASON_WEEKS + 1):
        for m in schedule:
            if m["matchupPeriodId"] != week:
                continue
            winner = m.get("winner", "UNDECIDED")
            if winner == "UNDECIDED":
                continue
            if m["home"]["teamId"] == team_id:
                results.append("W" if winner == "HOME" else "L")
            elif m["away"]["teamId"] == team_id:
                results.append("W" if winner == "AWAY" else "L")

    if not results:
        return "—"

    current = results[-1]
    count = 0
    for r in reversed(results):
        if r == current:
            count += 1
        else:
            break
    return f"{current}{count}"


def build_standings(teams_data, schedule):
    members = {
        m["id"]: m.get("firstName", "") + " " + m.get("lastName", "")
        for m in teams_data.get("members", [])
    }

    standings = []
    for t in sorted(teams_data["teams"], key=lambda x: x.get("playoffSeed", 99)):
        rec = t["record"]["overall"]
        owner_id = t.get("primaryOwner", "")
        streak = calc_streak(t["id"], schedule)
        standings.append({
            "rank":          t.get("playoffSeed", 0),
            "teamId":        t["id"],
            "name":          t.get("name", ""),
            "abbrev":        t.get("abbrev", ""),
            "owner":         members.get(owner_id, "").strip(),
            "wins":          rec["wins"],
            "losses":        rec["losses"],
            "pointsFor":     round(rec["pointsFor"], 1),
            "pointsAgainst": round(rec["pointsAgainst"], 1),
            "streak":        streak,
        })
    return standings


def build_schedule(teams_data, schedule):
    team_map = {t["id"]: t.get("name", "") for t in teams_data["teams"]}
    total_weeks = max(m["matchupPeriodId"] for m in schedule)

    weeks = {}
    for week in range(1, total_weeks + 1):
        matchups = []
        for m in sorted(
            [x for x in schedule if x["matchupPeriodId"] == week and "away" in x and "home" in x],
            key=lambda x: x["id"],
        ):
            home = m["home"]
            away = m["away"]
            winner = m.get("winner", "UNDECIDED")
            matchups.append({
                "away": {
                    "teamId": away["teamId"],
                    "name":   team_map.get(away["teamId"], ""),
                    "score":  round(away.get("totalPoints", 0), 2),
                    "winner": winner == "AWAY",
                },
                "home": {
                    "teamId": home["teamId"],
                    "name":   team_map.get(home["teamId"], ""),
                    "score":  round(home.get("totalPoints", 0), 2),
                    "winner": winner == "HOME",
                },
                "completed": winner != "UNDECIDED",
            })
        weeks[str(week)] = matchups

    return {"totalWeeks": total_weeks, "regularSeasonWeeks": REGULAR_SEASON_WEEKS, "weeks": weeks}


def main():
    os.makedirs("data", exist_ok=True)

    print("Fetching team data...")
    teams_data = fetch("mTeam")

    print("Fetching schedule data...")
    schedule_data = fetch("mMatchup")
    schedule = schedule_data.get("schedule", [])

    print("Building standings...")
    standings = build_standings(teams_data, schedule)
    with open("data/standings.json", "w") as f:
        json.dump({"season": SEASON, "standings": standings}, f, indent=2)
    print(f"  -> data/standings.json ({len(standings)} teams)")

    print("Building schedule...")
    sched = build_schedule(teams_data, schedule)
    with open("data/schedule.json", "w") as f:
        json.dump(sched, f, indent=2)
    print(f"  -> data/schedule.json ({sched['totalWeeks']} weeks)")

    print("\nDone. Commit and push the data/ folder to update the site.")


if __name__ == "__main__":
    main()
