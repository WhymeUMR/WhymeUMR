"""Draws the last 31 days of GitHub contributions as an SVG line chart.

Usage: GITHUB_TOKEN=... python activity_graph.py <user> <output.svg>
"""

import datetime as dt
import json
import os
import sys
import urllib.request

DAYS = 31
WIDTH, HEIGHT = 1000, 320
PAD_L, PAD_R, PAD_T, PAD_B = 56, 24, 56, 48

TITLE = "#9d4edd"
TEXT = "#c4b5fd"
LINE = "#9d4edd"
POINT = "#7c3aed"
GRID = "#3b0764"

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch_days(login: str, token: str) -> list[tuple[dt.date, int]]:
    today = dt.datetime.now(dt.timezone.utc).date()
    start = today - dt.timedelta(days=DAYS - 1)
    body = json.dumps({
        "query": QUERY,
        "variables": {
            "login": login,
            "from": f"{start}T00:00:00Z",
            "to": f"{today}T23:59:59Z",
        },
    }).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if "errors" in data:
        raise SystemExit(f"GraphQL error: {data['errors']}")

    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    counts = {
        dt.date.fromisoformat(d["date"]): d["contributionCount"]
        for w in weeks
        for d in w["contributionDays"]
    }
    return [(start + dt.timedelta(days=i), counts.get(start + dt.timedelta(days=i), 0)) for i in range(DAYS)]


def render(login: str, days: list[tuple[dt.date, int]]) -> str:
    peak = max(c for _, c in days)
    # Round the axis up to a multiple of 4 so the four grid steps get whole numbers.
    top = max(4, -(-peak // 4) * 4)
    plot_w = WIDTH - PAD_L - PAD_R
    plot_h = HEIGHT - PAD_T - PAD_B

    def x(i: int) -> float:
        return PAD_L + plot_w * i / (DAYS - 1)

    def y(v: int) -> float:
        return PAD_T + plot_h * (1 - v / top)

    pts = [(x(i), y(c)) for i, (_, c) in enumerate(days)]
    line = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    base = y(0)
    area = f"{pts[0][0]:.1f},{base:.1f} {line} {pts[-1][0]:.1f},{base:.1f}"

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" font-family="JetBrains Mono, ui-monospace, monospace">',
        f'<text x="{WIDTH / 2}" y="30" fill="{TITLE}" font-size="18" font-weight="700" '
        f'text-anchor="middle">{login}\'s Contribution Graph</text>',
    ]
    for step in range(5):
        v = top * step // 4
        gy = y(v)
        out.append(f'<line x1="{PAD_L}" y1="{gy:.1f}" x2="{WIDTH - PAD_R}" y2="{gy:.1f}" '
                   f'stroke="{GRID}" stroke-dasharray="3 4"/>')
        out.append(f'<text x="{PAD_L - 10}" y="{gy + 4:.1f}" fill="{TEXT}" font-size="11" '
                   f'text-anchor="end">{v}</text>')
    for i, (day, _) in enumerate(days):
        out.append(f'<text x="{x(i):.1f}" y="{HEIGHT - PAD_B + 20}" fill="{TEXT}" '
                   f'font-size="11" text-anchor="middle">{day.day}</text>')
    out.append(f'<text x="{WIDTH / 2}" y="{HEIGHT - 6}" fill="{TEXT}" font-size="11" '
               f'text-anchor="middle">Days</text>')
    out.append(f'<text x="14" y="{PAD_T + plot_h / 2}" fill="{TEXT}" font-size="11" '
               f'text-anchor="middle" transform="rotate(-90 14 {PAD_T + plot_h / 2})">Contributions</text>')
    out.append(f'<polygon points="{area}" fill="{LINE}" fill-opacity="0.18"/>')
    out.append(f'<polyline points="{line}" fill="none" stroke="{LINE}" stroke-width="2.5" '
               f'stroke-linejoin="round"/>')
    for (px, py), (day, c) in zip(pts, days):
        out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="{POINT}">'
                   f'<title>{day:%d %b}: {c}</title></circle>')
    out.append("</svg>")
    return "\n".join(out)


def main() -> None:
    login, path = sys.argv[1], sys.argv[2]
    days = fetch_days(login, os.environ["GITHUB_TOKEN"])
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write(render(login, days))


if __name__ == "__main__":
    main()
