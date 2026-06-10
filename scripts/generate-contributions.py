#!/usr/bin/env python3
"""
Generates a merged contribution heatmap across multiple GitHub accounts
and writes it to contributions.svg (github-dark theme).
Runs daily via GitHub Actions.
"""

import datetime
import json
import os
import urllib.request

USERS = ["vivekptnk", "vivek-rdc", "vivekptnk1"]
OUTPUT_PATH = "contributions.svg"

CELL = 10
GAP = 3
PITCH = CELL + GAP
LEFT = 28    # room for day labels
TOP = 20     # room for month labels
BOTTOM = 26  # room for total + legend

# github-dark palette: empty, then levels 1-4
COLORS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
TEXT_COLOR = "#8b949e"
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch_calendar(login, token):
    """Fetch one user's contribution calendar as a {date: count} dict."""
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())

    if data.get("errors"):
        raise RuntimeError(f"GraphQL error for {login}: {data['errors']}")

    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return {d["date"]: d["contributionCount"] for w in weeks for d in w["contributionDays"]}


def merge_calendars(calendars):
    """Sum contribution counts across accounts by date."""
    merged = {}
    for cal in calendars:
        for date, count in cal.items():
            merged[date] = merged.get(date, 0) + count
    return merged


def make_level(counts):
    """Map a count to a color level (0-4) using quartiles of nonzero days."""
    nonzero = sorted(c for c in counts if c > 0)
    if not nonzero:
        return lambda c: 0
    q = lambda p: nonzero[min(len(nonzero) - 1, int(len(nonzero) * p))]
    t1, t2, t3 = q(0.25), q(0.5), q(0.75)

    def level(count):
        if count == 0:
            return 0
        if count <= t1:
            return 1
        if count <= t2:
            return 2
        if count <= t3:
            return 3
        return 4

    return level


def render_svg(merged):
    dates = sorted(merged)
    first = datetime.date.fromisoformat(dates[0])
    # Grid columns are weeks starting on Sunday, like github.com
    start_sunday = first - datetime.timedelta(days=(first.weekday() + 1) % 7)
    level = make_level(merged.values())

    cells = []
    col_first_date = {}
    for iso in dates:
        d = datetime.date.fromisoformat(iso)
        col = (d - start_sunday).days // 7
        row = (d.weekday() + 1) % 7
        if col not in col_first_date:
            col_first_date[col] = d
        x = LEFT + col * PITCH
        y = TOP + row * PITCH
        cells.append(
            f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" '
            f'fill="{COLORS[level(merged[iso])]}"/>'
        )

    cols = max(col_first_date) + 1
    width = LEFT + cols * PITCH + 2
    height = TOP + 7 * PITCH + BOTTOM

    # Month labels: mark each column where the month changes
    months = []
    prev_month = None
    for col in sorted(col_first_date):
        m = col_first_date[col].month
        if m != prev_month and prev_month is not None:
            months.append(
                f'<text x="{LEFT + col * PITCH}" y="{TOP - 7}" fill="{TEXT_COLOR}" '
                f'font-size="10">{col_first_date[col].strftime("%b")}</text>'
            )
        prev_month = m

    day_labels = [
        f'<text x="{LEFT - 6}" y="{TOP + row * PITCH + CELL - 1}" fill="{TEXT_COLOR}" '
        f'font-size="10" text-anchor="end">{name}</text>'
        for row, name in [(1, "M"), (3, "W"), (5, "F")]
    ]

    total = sum(merged.values())
    footer_y = TOP + 7 * PITCH + 16
    footer = [
        f'<text x="{LEFT}" y="{footer_y}" fill="{TEXT_COLOR}" font-size="10">'
        f'{total:,} contributions in the last year across {len(USERS)} accounts</text>',
        f'<text x="{width - 2 - 5 * PITCH - 34}" y="{footer_y}" fill="{TEXT_COLOR}" '
        f'font-size="10" text-anchor="end">Less</text>',
    ]
    for i, color in enumerate(COLORS):
        x = width - 2 - (5 - i) * PITCH - 30
        footer.append(
            f'<rect x="{x}" y="{footer_y - 8}" width="{CELL}" height="{CELL}" rx="2" fill="{color}"/>'
        )
    footer.append(
        f'<text x="{width - 2}" y="{footer_y}" fill="{TEXT_COLOR}" '
        f'font-size="10" text-anchor="end">More</text>'
    )

    parts = months + day_labels + cells + footer
    body = "\n".join(parts)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{FONT}">\n{body}\n</svg>\n'
    )


if __name__ == "__main__":
    token = os.environ["GITHUB_TOKEN"]
    calendars = [fetch_calendar(user, token) for user in USERS]
    merged = merge_calendars(calendars)
    svg = render_svg(merged)
    with open(OUTPUT_PATH, "w") as f:
        f.write(svg)
    print(f"Wrote {OUTPUT_PATH}: {sum(merged.values()):,} total contributions across {len(USERS)} accounts.")
