"""Check that GitHub Actions scheduled workflows have been running on time.

Compares expected cron fire times against actual `event=schedule` runs from the
GitHub API, and flags missed runs, failed runs, and workflows that GitHub has
auto-disabled (e.g. after 60 days of repo inactivity).

Usage:
    python scripts/check_workflow_schedules.py            # per-workflow default lookback
    python scripts/check_workflow_schedules.py --days 30  # override lookback for all

Auth: uses GITHUB_TOKEN env var if set, otherwise falls back to the token
stored in the local git credential helper (same one used for `git push`).
No external dependencies (stdlib only).
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

OWNER = "shelmasalsa17"
REPO = "Dashboard-Pertamina-VeloCT"
WIB = timezone(timedelta(hours=7))

# GitHub cron scheduling is best-effort: observed delays on this repo are
# 3-5 hours. A run within this window still counts as "ran".
MATCH_WINDOW = timedelta(hours=6)

# workflow file -> (label, cron, lookback_days)
WORKFLOWS = {
    "daily_morning.yml": ("Daily Morning", "0 1 * * 1-5", 14),
    "daily_afternoon.yml": ("Daily Afternoon", "0 7 * * 1-5", 14),
    "weekly.yml": ("Weekly", "0 1 * * 1", 35),
    "monthly.yml": ("Monthly", "0 1 1 * *", 120),
}


def get_token():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    try:
        out = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            capture_output=True, text=True, timeout=15, check=True,
        ).stdout
        for line in out.splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1]
    except (subprocess.SubprocessError, OSError):
        pass
    sys.exit("ERROR: no GitHub token. Set GITHUB_TOKEN or configure git credentials.")


def api_get(path, token, params=None):
    url = f"https://api.github.com{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


# ---- minimal 5-field cron parser (minute hour dom month dow) ----

def parse_field(field, lo, hi):
    """Expand one cron field into a set of ints. Supports * , - / and numbers."""
    values = set()
    for part in field.split(","):
        step = 1
        if "/" in part:
            part, step_s = part.split("/")
            step = int(step_s)
        if part == "*":
            start, end = lo, hi
        elif "-" in part:
            a, b = part.split("-")
            start, end = int(a), int(b)
        else:
            start = end = int(part)
        values.update(range(start, end + 1, step))
    return values


def cron_times_between(cron, start, end):
    """All UTC datetimes in (start, end] matching the cron expression."""
    minute_f, hour_f, dom_f, month_f, dow_f = cron.split()
    minutes = parse_field(minute_f, 0, 59)
    hours = parse_field(hour_f, 0, 23)
    doms = parse_field(dom_f, 1, 31)
    months = parse_field(month_f, 1, 12)
    dows = parse_field(dow_f, 0, 7)
    dows = {d % 7 for d in dows}  # cron: 0 and 7 both = Sunday
    dom_any = dom_f == "*"
    dow_any = dow_f == "*"

    times = []
    day = start.replace(hour=0, minute=0, second=0, microsecond=0)
    while day <= end:
        cron_dow = (day.weekday() + 1) % 7  # python Mon=0 -> cron Sun=0
        dom_ok = day.day in doms
        dow_ok = cron_dow in dows
        # standard cron: if both dom and dow are restricted, either may match
        if day.month in months and (
            (dom_ok and dow_ok) or (dom_any and dow_ok) or (dow_any and dom_ok)
        ):
            for h in sorted(hours):
                for m in sorted(minutes):
                    t = day.replace(hour=h, minute=m)
                    if start < t <= end:
                        times.append(t)
        day += timedelta(days=1)
    return times


def parse_ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def fetch_scheduled_runs(token, wf_file, since):
    """All schedule-triggered runs of a workflow since `since` (paginated)."""
    runs = []
    page = 1
    while page <= 10:
        data = api_get(
            f"/repos/{OWNER}/{REPO}/actions/workflows/{wf_file}/runs",
            token,
            {"event": "schedule", "per_page": 100, "page": page,
             "created": f">={since.strftime('%Y-%m-%d')}"},
        )
        batch = data.get("workflow_runs", [])
        runs.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return runs


def check_workflow(token, wf_file, label, cron, lookback_days, now):
    print(f"\n=== {label} ({wf_file}) — cron: {cron} ===")

    wf = api_get(f"/repos/{OWNER}/{REPO}/actions/workflows/{wf_file}", token)
    state = wf.get("state")
    if state != "active":
        print(f"  !! WORKFLOW STATE: {state} — scheduler is NOT running "
              f"(GitHub disables schedules after 60 days of repo inactivity; "
              f"re-enable in the Actions tab)")

    since = now - timedelta(days=lookback_days)
    # cron can only fire after the workflow was registered on the default branch
    registered = datetime.fromisoformat(wf["created_at"]).astimezone(timezone.utc)
    if registered > since:
        print(f"  (workflow registered {registered.astimezone(WIB):%Y-%m-%d %H:%M} WIB — "
              f"checking from there)")
        since = registered
    expected = cron_times_between(cron, since, now)
    runs = fetch_scheduled_runs(token, wf_file, since)
    run_times = [(parse_ts(r["run_started_at"]), r) for r in runs]

    missed, failed, ok = [], [], 0
    used_run_ids = set()
    for exp in expected:
        # nearest unmatched run started within [exp, exp + MATCH_WINDOW]
        candidates = [
            (started, r) for started, r in run_times
            if r["id"] not in used_run_ids and exp <= started <= exp + MATCH_WINDOW
        ]
        if not candidates:
            if now - exp < MATCH_WINDOW:
                print(f"  .. {exp.astimezone(WIB):%a %Y-%m-%d %H:%M} WIB — "
                      f"pending (still within {MATCH_WINDOW} grace window)")
            else:
                missed.append(exp)
            continue
        started, run = min(candidates, key=lambda c: c[0])
        used_run_ids.add(run["id"])
        delay = int((started - exp).total_seconds() // 60)
        concl = run["conclusion"] or run["status"]
        line = (f"{exp.astimezone(WIB):%a %Y-%m-%d %H:%M} WIB — "
                f"ran +{delay}min, {concl}")
        if concl == "success":
            ok += 1
            print(f"  OK {line}")
        else:
            failed.append((exp, run))
            print(f"  XX {line}  {run['html_url']}")

    for exp in missed:
        print(f"  XX {exp.astimezone(WIB):%a %Y-%m-%d %H:%M} WIB — MISSED (no scheduled run)")

    total = len(expected)
    print(f"  -> {ok}/{total} on schedule & successful, "
          f"{len(failed)} failed, {len(missed)} missed "
          f"(lookback {lookback_days}d)")
    return state == "active" and not missed and not failed


def main():
    ap = argparse.ArgumentParser(description="Check GitHub Actions cron schedules ran on time")
    ap.add_argument("--days", type=int, default=None,
                    help="override lookback days for all workflows")
    args = ap.parse_args()

    token = get_token()
    now = datetime.now(timezone.utc)
    print(f"Repo: {OWNER}/{REPO}")
    print(f"Now:  {now:%Y-%m-%d %H:%M} UTC / {now.astimezone(WIB):%Y-%m-%d %H:%M} WIB")

    all_ok = True
    for wf_file, (label, cron, lookback) in WORKFLOWS.items():
        days = args.days or lookback
        try:
            if not check_workflow(token, wf_file, label, cron, days, now):
                all_ok = False
        except Exception as e:
            print(f"  ERROR checking {wf_file}: {e}")
            all_ok = False

    print("\n" + ("ALL SCHEDULERS HEALTHY" if all_ok
                  else "PROBLEMS FOUND — see XX / !! lines above"))
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
