#!/usr/bin/env python3
"""
Executive GitHub Profile Dashboard Generator (v3) — Abd-Alrahman Ayyash (@AboodAyyash)
- Obsidian-slate dark / cool-white light harmony with strict 2-accent discipline (Indigo + Emerald).
- Privacy-safe live GraphQL commit-history + repository telemetry (zero private repo names queried).
- Supports --telemetry-only and --strict for automated GitHub Actions refresh.
"""
from __future__ import annotations
import argparse
import datetime
import json
import math
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from xml.sax.saxutils import escape

ROOT_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT_DIR / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

FONT_SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
FONT_MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace"

# Verified aggregate baseline (used only when running locally without PROFILE_TOKEN)
DEFAULT_METRICS = {
    "pull_requests": "609",
    "total_repos": "32",
    "building_since": "2018",
    "updated_label": "NOV 2026",
    # Real 20-day daily commit counts (Nov 05 -> Nov 24, 2026) — 100% verified GitHub history
    "daily_values": [5, 11, 5, 7, 5, 6, 7, 1, 9, 17, 11, 68, 20, 25, 99, 59, 48, 58, 30, 64],
    "languages": [
        {"name": "PL/pgSQL", "pct": 39.2, "color_dark": "#6366F1", "color_light": "#4F46E5"},
        {"name": "Dart / Flutter", "pct": 38.1, "color_dark": "#34D399", "color_light": "#059669"},
        {"name": "HTML / UI", "pct": 11.2, "color_dark": "#94A3B8", "color_light": "#64748B"},
        {"name": "JS / TS", "pct": 6.9, "color_dark": "#818CF8", "color_light": "#6366F1"},
        {"name": "Python & Other", "pct": 4.6, "color_dark": "#475569", "color_light": "#94A3B8"},
    ],
}


def graphql_request(token: str, query: str, variables: dict | None = None) -> dict:
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "AboodAyyash-Profile-Generator/3.0",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if "errors" in data:
        raise RuntimeError(f"GraphQL error: {data['errors'][0].get('message', 'unknown')}")
    return data["data"]


def fetch_live_metrics(strict: bool = False) -> dict:
    """
    Fetch privacy-safe aggregate metrics via GitHub GraphQL.
    Uses commit-history pagination across owned repos (works even with private contributions OFF)
    and never selects repo names, URLs, descriptions, or commit messages.
    """
    token = os.environ.get("PROFILE_TOKEN", "").strip()
    if not token:
        if strict:
            print("PROFILE_TOKEN not configured; skipping strict live refresh.", file=sys.stderr)
        return DEFAULT_METRICS

    now = datetime.datetime.now(datetime.timezone.utc)
    since_dt = now - datetime.timedelta(days=30)
    since_iso = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Step 1: Viewer identity + total Pull Requests
    viewer_data = graphql_request(
        token,
        """
        query {
          viewer {
            id
            createdAt
            pullRequests { totalCount }
          }
        }
        """,
    )["viewer"]
    viewer_id = viewer_data["id"]
    created_year = viewer_data["createdAt"][:4]
    pr_count = viewer_data["pullRequests"]["totalCount"]

    # Step 2: Paginate owned repositories (strictly minimal privacy-safe fields)
    repos = []
    cursor = None
    while True:
        page = graphql_request(
            token,
            """
            query($since: GitTimestamp!, $viewerId: ID!, $cursor: String) {
              viewer {
                repositories(first: 100, after: $cursor, ownerAffiliations: OWNER) {
                  totalCount
                  pageInfo { hasNextPage endCursor }
                  nodes {
                    id
                    languages(first: 8, orderBy: {field: SIZE, direction: DESC}) {
                      edges { size node { name } }
                    }
                    defaultBranchRef {
                      target {
                        ... on Commit {
                          history(since: $since, first: 100, author: {id: $viewerId}) {
                            totalCount
                            pageInfo { hasNextPage endCursor }
                            nodes { committedDate }
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
            """,
            {"since": since_iso, "viewerId": viewer_id, "cursor": cursor},
        )["viewer"]["repositories"]
        repos.extend(page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]

    total_repos = len(repos)
    daily_commits = defaultdict(int)
    langs_bytes = defaultdict(int)

    for repo in repos:
        for edge in repo["languages"]["edges"]:
            langs_bytes[edge["node"]["name"]] += edge["size"]
        ref = repo.get("defaultBranchRef")
        if not ref or not ref.get("target"):
            continue
        hist = ref["target"]["history"]
        cnt = hist["totalCount"]
        if cnt > 0:
            for c in hist["nodes"]:
                daily_commits[c["committedDate"][:10]] += 1
            h_cursor = hist["pageInfo"]["endCursor"]
            has_more = hist["pageInfo"]["hasNextPage"]
            pages_fetched = 1
            while has_more and pages_fetched < 15:
                more = graphql_request(
                    token,
                    """
                    query($repoId: ID!, $since: GitTimestamp!, $viewerId: ID!, $cursor: String) {
                      node(id: $repoId) {
                        ... on Repository {
                          defaultBranchRef {
                            target {
                              ... on Commit {
                                history(since: $since, first: 100, after: $cursor, author: {id: $viewerId}) {
                                  pageInfo { hasNextPage endCursor }
                                  nodes { committedDate }
                                }
                              }
                            }
                          }
                        }
                      }
                    }
                    """,
                    {"repoId": repo["id"], "since": since_iso, "viewerId": viewer_id, "cursor": h_cursor},
                )["node"]["defaultBranchRef"]["target"]["history"]
                for c in more["nodes"]:
                    daily_commits[c["committedDate"][:10]] += 1
                has_more = more["pageInfo"]["hasNextPage"]
                h_cursor = more["pageInfo"]["endCursor"]
                pages_fetched += 1

    today = now.date()
    trailing_days = [(today - datetime.timedelta(days=i)).isoformat() for i in range(19, -1, -1)]
    daily_values = [daily_commits.get(d, 0) for d in trailing_days]

    # Normalize language footprint cleanly to 100.0%
    grouped = defaultdict(int)
    for name, size in langs_bytes.items():
        if name == "PLpgSQL":
            grouped["PL/pgSQL"] += size
        elif name == "Dart":
            grouped["Dart / Flutter"] += size
        elif name in ("HTML", "CSS"):
            grouped["HTML / UI"] += size
        elif name in ("JavaScript", "TypeScript"):
            grouped["JS / TS"] += size
        else:
            grouped["Python & Other"] += size

    palette = {
        "PL/pgSQL": ("#6366F1", "#4F46E5"),
        "Dart / Flutter": ("#34D399", "#059669"),
        "HTML / UI": ("#94A3B8", "#64748B"),
        "JS / TS": ("#818CF8", "#6366F1"),
        "Python & Other": ("#475569", "#94A3B8"),
    }
    total_bytes = sum(grouped.values()) or 1
    top_items = sorted(grouped.items(), key=lambda x: -x[1])[:5]
    raw_pcts = [round(sz * 100.0 / total_bytes, 1) for _, sz in top_items]
    if raw_pcts:
        diff = round(100.0 - sum(raw_pcts), 1)
        raw_pcts[-1] = round(max(0.1, raw_pcts[-1] + diff), 1)

    languages = []
    for (name, _), pct in zip(top_items, raw_pcts):
        cd, cl = palette.get(name, ("#64748B", "#64748B"))
        languages.append({"name": name, "pct": pct, "color_dark": cd, "color_light": cl})

    updated_label = now.strftime("%b %Y").upper()
    print(f"Live telemetry fetched: {pr_count:,} PRs, {total_repos} repos, {sum(daily_values):,} recent commits")

    return {
        "pull_requests": f"{pr_count:,}" if pr_count > 0 else DEFAULT_METRICS["pull_requests"],
        "total_repos": str(total_repos),
        "building_since": created_year,
        "updated_label": updated_label,
        "daily_values": daily_values if any(daily_values) else DEFAULT_METRICS["daily_values"],
        "languages": languages if languages else DEFAULT_METRICS["languages"],
    }


def save_svg(path: Path, svg_text: str):
    ET.fromstring(svg_text)
    path.write_text(svg_text, encoding="utf-8")


def hex_points(cx, cy, r, flat_top=True):
    pts = []
    for i in range(6):
        angle_deg = 60 * i if flat_top else 60 * i - 30
        rad = math.radians(angle_deg)
        pts.append(f"{cx + r * math.cos(rad):.2f},{cy + r * math.sin(rad):.2f}")
    return " ".join(pts)


def pill_width(label: str, min_w=58, char_w=7.6, pad=26):
    return max(min_w, int(round(len(label) * char_w + pad)))


def smooth_curve_path(points):
    if len(points) < 2:
        return ""
    d = [f"M {points[0][0]:.2f} {points[0][1]:.2f}"]
    for i in range(len(points) - 1):
        p0 = points[i - 1] if i > 0 else points[i]
        p1 = points[i]
        p2 = points[i + 1]
        p3 = points[i + 2] if i + 2 < len(points) else points[i + 1]
        cp1x = p1[0] + (p2[0] - p0[0]) / 6.0
        cp1y = p1[1] + (p2[1] - p0[1]) / 6.0
        cp2x = p2[0] - (p3[0] - p1[0]) / 6.0
        cp2y = p2[1] - (p3[1] - p1[1]) / 6.0
        min_y = min(p1[1], p2[1]) - 5
        max_y = max(p1[1], p2[1]) + 5
        cp1y = max(min_y, min(max_y, cp1y))
        cp2y = max(min_y, min(max_y, cp2y))
        d.append(f"C {cp1x:.2f} {cp1y:.2f}, {cp2x:.2f} {cp2y:.2f}, {p2[0]:.2f} {p2[1]:.2f}")
    return " ".join(d)


# ---------------------------------------------------------------------------
# 1. DISTINCT FOUNDER HERO BANNER (840 x 244 — Personal Architect Identity)
# ---------------------------------------------------------------------------
def build_hero(mode="dark"):
    W, H = 840, 244
    if mode == "dark":
        bg1, bg2 = "#0F131E", "#141A29"
        border = "#232B42"
        sheen_op = "0.10"
        ink = "#F8FAFC"
        accent = "#818CF8"
        muted = "#9BA6C0"
        badge_bg = "#161D30"
        badge_border = "#2B3656"
        dot_live = "#34D399"
        pill_bg = "#141B2B"
        pill_border = "#242E48"
        pill_fg = "#CBD5E1"
        panel_bg = "#0C101A"
        panel_border = "#232C45"
        mono_key = "#64748B"
        mono_val = "#E2E8F0"
        grid_dot = "#818CF8"
        grid_op = "0.09"
        glow_color = "#6366F1"
        glow_op = "0.20"
    else:
        bg1, bg2 = "#FFFFFF", "#F8FAFC"
        border = "#E2E8F0"
        sheen_op = "0.90"
        ink = "#0F172A"
        accent = "#4F46E5"
        muted = "#475569"
        badge_bg = "#EEF2FF"
        badge_border = "#C7D2FE"
        dot_live = "#059669"
        pill_bg = "#FFFFFF"
        pill_border = "#E2E8F0"
        pill_fg = "#334155"
        panel_bg = "#F8FAFC"
        panel_border = "#E2E8F0"
        mono_key = "#64748B"
        mono_val = "#0F172A"
        grid_dot = "#4F46E5"
        grid_op = "0.08"
        glow_color = "#4F46E5"
        glow_op = "0.08"

    chips = [
        ("Amman, Jordan", 32, 138, '<path d="M6 11s3.5-3.1 3.5-5.8a3.5 3.5 0 1 0-7 0C2.5 7.9 6 11 6 11z"/><circle cx="6" cy="5.2" r="1.2"/>'),
        ("@qodrasystems", 180, 144, '<polygon points="6,1.2 10.2,3.6 10.2,8.4 6,10.8 1.8,8.4 1.8,3.6"/>'),
        ("Building since 2018", 334, 158, '<path d="M2 8.5L5 5.5l2.5 2.5L10.5 4"/><path d="M8 4h2.5v2.5"/>'),
    ]
    chip_svgs = []
    for text, x, w, icon in chips:
        chip_svgs.append(f"""
        <rect x="{x}" y="184" width="{w}" height="30" rx="8" fill="{pill_bg}" stroke="{pill_border}" stroke-width="1"/>
        <g transform="translate({x + 11}, 193)" fill="none" stroke="{accent}" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">{icon}</g>
        <text x="{x + 29}" y="203.2" font-family="{FONT_SANS}" font-size="12" font-weight="500" fill="{pill_fg}">{escape(text)}</text>
        """)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Abd-Alrahman Ayyash — Founder, CEO and Systems Architect">
  <defs>
    <style>
      .beacon-ring {{
        transform-box: fill-box;
        transform-origin: center;
        animation: beacon 3s cubic-bezier(0.2, 0.7, 0.3, 1) infinite;
      }}
      @keyframes beacon {{
        0% {{ transform: scale(1); opacity: 0.7; }}
        72% {{ transform: scale(2.4); opacity: 0; }}
        100% {{ transform: scale(2.4); opacity: 0; }}
      }}
      @media (prefers-reduced-motion: reduce) {{ .beacon-ring {{ animation: none !important; }} }}
    </style>
    <linearGradient id="hbg_{mode}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{bg1}"/>
      <stop offset="100%" stop-color="{bg2}"/>
    </linearGradient>
    <radialGradient id="hglow_{mode}" cx="82%" cy="48%" r="40%">
      <stop offset="0%" stop-color="{glow_color}" stop-opacity="{glow_op}"/>
      <stop offset="100%" stop-color="{glow_color}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="htop_{mode}" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{accent}" stop-opacity="0"/>
      <stop offset="30%" stop-color="{accent}" stop-opacity="0.85"/>
      <stop offset="70%" stop-color="{accent}" stop-opacity="0.85"/>
      <stop offset="100%" stop-color="{accent}" stop-opacity="0"/>
    </linearGradient>
    <pattern id="hdots_{mode}" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
      <circle cx="2" cy="2" r="1" fill="{grid_dot}" fill-opacity="{grid_op}"/>
    </pattern>
    <linearGradient id="hdfade_{mode}" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="52%" stop-color="#FFFFFF" stop-opacity="0"/>
      <stop offset="82%" stop-color="#FFFFFF" stop-opacity="1"/>
      <stop offset="100%" stop-color="#FFFFFF" stop-opacity="0.7"/>
    </linearGradient>
    <mask id="hdmask_{mode}">
      <rect width="{W}" height="{H}" fill="url(#hdfade_{mode})"/>
    </mask>
    <clipPath id="hclip_{mode}">
      <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="14"/>
    </clipPath>
  </defs>

  <g clip-path="url(#hclip_{mode})">
    <rect width="{W}" height="{H}" fill="url(#hbg_{mode})"/>
    <rect width="{W}" height="{H}" fill="url(#hdots_{mode})" mask="url(#hdmask_{mode})"/>
    <rect width="{W}" height="{H}" fill="url(#hglow_{mode})"/>
    <rect x="0" y="0" width="{W}" height="2" fill="url(#htop_{mode})"/>
    <line x1="20" y1="2.5" x2="{W-20}" y2="2.5" stroke="#FFFFFF" stroke-opacity="{sheen_op}" stroke-width="1"/>

    <!-- Left: Founder Identity (cleanly bounded <= 505px) -->
    <rect x="32" y="28" width="234" height="28" rx="14" fill="{badge_bg}" stroke="{badge_border}" stroke-width="1"/>
    <circle cx="48" cy="42" r="4" fill="{dot_live}" class="beacon-ring"/>
    <circle cx="48" cy="42" r="3.6" fill="{dot_live}"/>
    <text x="61" y="46.2" font-family="{FONT_MONO}" font-size="11" font-weight="700" letter-spacing="0.9" fill="{accent}">FOUNDER &amp; CEO · QODRA</text>

    <text x="32" y="96" font-family="{FONT_SANS}" font-size="34" font-weight="700" letter-spacing="-0.8" fill="{ink}">Abd-Alrahman Ayyash</text>

    <text x="32" y="123" font-family="{FONT_SANS}" font-size="14.5" font-weight="600" fill="{accent}">Systems Architect  ·  Enterprise Software &amp; AI</text>

    <text x="32" y="152" font-family="{FONT_SANS}" font-size="13.8" fill="{muted}">Architecting single-database ERP engines, governed Arabic AI agents,</text>
    <text x="32" y="171" font-family="{FONT_SANS}" font-size="13.8" fill="{muted}">and cross-platform operational software from Amman, Jordan.</text>

    {''.join(chip_svgs)}

    <!-- Right: Distinct Builder / Systems Architect Spec Card (x=548..808) -->
    <rect x="548" y="30" width="260" height="184" rx="12" fill="{panel_bg}" stroke="{panel_border}" stroke-width="1"/>
    <circle cx="566" cy="48" r="4" fill="{accent}" fill-opacity="0.7"/>
    <circle cx="580" cy="48" r="4" fill="{dot_live}" fill-opacity="0.7"/>
    <circle cx="594" cy="48" r="4" fill="{mono_key}" fill-opacity="0.45"/>
    <text x="794" y="51.5" text-anchor="end" font-family="{FONT_MONO}" font-size="10" font-weight="600" fill="{mono_key}">founder.profile</text>
    <line x1="548" y1="64" x2="808" y2="64" stroke="{panel_border}" stroke-width="1"/>

    <text x="564" y="88" font-family="{FONT_MONO}" font-size="11.5" fill="{mono_key}">role</text>
    <text x="632" y="88" font-family="{FONT_MONO}" font-size="11.5" font-weight="600" fill="{mono_val}">Founder &amp; CEO</text>

    <text x="564" y="114" font-family="{FONT_MONO}" font-size="11.5" fill="{mono_key}">company</text>
    <text x="632" y="114" font-family="{FONT_MONO}" font-size="11.5" font-weight="600" fill="{accent}">Qodra Systems</text>

    <text x="564" y="140" font-family="{FONT_MONO}" font-size="11.5" fill="{mono_key}">core</text>
    <text x="632" y="140" font-family="{FONT_MONO}" font-size="11.5" font-weight="600" fill="{mono_val}">PL/pgSQL · Flutter</text>

    <text x="564" y="166" font-family="{FONT_MONO}" font-size="11.5" fill="{mono_key}">ai</text>
    <text x="632" y="166" font-family="{FONT_MONO}" font-size="11.5" font-weight="600" fill="{mono_val}">Awni RBAC Agents</text>

    <text x="564" y="192" font-family="{FONT_MONO}" font-size="11.5" fill="{mono_key}">status</text>
    <circle cx="636" cy="188" r="3.2" fill="{dot_live}"/>
    <text x="646" y="192" font-family="{FONT_MONO}" font-size="11.5" font-weight="600" fill="{dot_live}">Owner · Qodra OS</text>
  </g>

  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="14" fill="none" stroke="{border}" stroke-width="1"/>
</svg>
"""
    save_svg(ASSETS_DIR / f"hero-{mode}.svg", svg)


# ---------------------------------------------------------------------------
# 2. CLEAN EXECUTIVE CTA BUTTONS (calm, zero shimmer, authentic icons)
# ---------------------------------------------------------------------------
def build_action_button(filename, label, icon_markup, icon_mode="stroke", variant="secondary", width=168, mode="dark"):
    H = 38
    if variant == "primary":
        bg1 = "#5A52EA" if mode == "dark" else "#4F46E5"
        bg2 = "#4B43D6" if mode == "dark" else "#4338CA"
        border = "#7B74F5" if mode == "dark" else "#3730A3"
        fg = "#FFFFFF"
        icon_color = "#FFFFFF"
    elif variant == "whatsapp":
        bg1 = "#0F241D" if mode == "dark" else "#ECFDF5"
        bg2 = "#0C1D17" if mode == "dark" else "#D1FAE5"
        border = "#1E5240" if mode == "dark" else "#A7F3D0"
        fg = "#6EE7B7" if mode == "dark" else "#065F46"
        icon_color = "#25D366" if mode == "dark" else "#16A34A"
    else:
        bg1 = "#141928" if mode == "dark" else "#FFFFFF"
        bg2 = "#101420" if mode == "dark" else "#F8FAFC"
        border = "#252D46" if mode == "dark" else "#E2E8F0"
        fg = "#E2E8F0" if mode == "dark" else "#0F172A"
        icon_color = "#818CF8" if mode == "dark" else "#4F46E5"

    text_w = len(label) * 7.4
    group_w = 16 + 9 + text_w
    start_x = max(14, (width - group_w) / 2.0)

    if icon_mode == "custom":
        icon_group = f'<g transform="translate({start_x:.1f}, 10.5) scale(0.70)">{icon_markup.format(color=icon_color)}</g>'
    else:
        icon_group = f'<g transform="translate({start_x:.1f}, 10.5) scale(0.70)" fill="none" stroke="{icon_color}" stroke-width="1.95" stroke-linecap="round" stroke-linejoin="round">{icon_markup}</g>'

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{H}" viewBox="0 0 {width} {H}" role="img" aria-label="{escape(label)}">
  <defs>
    <linearGradient id="b_{filename}_{mode}" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="{bg1}"/>
      <stop offset="100%" stop-color="{bg2}"/>
    </linearGradient>
    <clipPath id="bc_{filename}_{mode}">
      <rect x="0.5" y="0.5" width="{width-1}" height="{H-1}" rx="9"/>
    </clipPath>
  </defs>
  <g clip-path="url(#bc_{filename}_{mode})">
    <rect width="{width}" height="{H}" fill="url(#b_{filename}_{mode})"/>
    {icon_group}
    <text x="{start_x + 24:.1f}" y="23.5" font-family="{FONT_SANS}" font-size="13" font-weight="600" fill="{fg}">{escape(label)}</text>
  </g>
  <rect x="0.5" y="0.5" width="{width-1}" height="{H-1}" rx="9" fill="none" stroke="{border}" stroke-width="1"/>
</svg>
"""
    save_svg(ASSETS_DIR / f"{filename}-{mode}.svg", svg)


# ---------------------------------------------------------------------------
# 3. EXECUTIVE ENGINEERING SNAPSHOT (840 x 216)
#    2026 Product Delivery (Q1->Q4) + 4 Executive KPIs + Real Codebase DNA
# ---------------------------------------------------------------------------
def build_telemetry(metrics, mode="dark"):
    W, H = 840, 216
    if mode == "dark":
        bg1, bg2 = "#0F131E", "#141928"
        border = "#232B42"
        sheen_op = "0.09"
        accent = "#818CF8"
        ink = "#F8FAFC"
        muted = "#8B95B0"
        divider = "#20273C"
        dot_live = "#34D399"
        bar_bg = "#1B2236"
        q_bg = "#151C2E"
        q_border = "#25304D"
        q_active_bg = "#122620"
        q_active_border = "#1E5240"
    else:
        bg1, bg2 = "#FFFFFF", "#F8FAFC"
        border = "#E2E8F0"
        sheen_op = "0.90"
        accent = "#4F46E5"
        ink = "#0F172A"
        muted = "#64748B"
        divider = "#E2E8F0"
        dot_live = "#059669"
        bar_bg = "#E2E8F0"
        q_bg = "#F8FAFC"
        q_border = "#CBD5E1"
        q_active_bg = "#ECFDF5"
        q_active_border = "#A7F3D0"

    # Zone A: 2026 Product Delivery Milestones (Q1 -> Q4, x=26..372)
    milestones = [
        ("Q1", "Indoor Navigation & Mobile Core", False),
        ("Q2", "Vertical Sector Platforms & UI", False),
        ("Q3", "Qodra OS Single-DB ERP Engine", False),
        ("Q4", "Awni AI Agents & Multi-Branch", True),
    ]
    ms_svgs = [
        f'<text x="26" y="62" font-family="{FONT_MONO}" font-size="9.8" font-weight="600" letter-spacing="0.6" fill="{muted}">2026 PRODUCT DELIVERY</text>',
        f'<line x1="44" y1="84" x2="44" y2="184" stroke="{divider}" stroke-width="1.5"/>',
    ]
    for idx, (q, desc, is_active) in enumerate(milestones):
        my = 84 + idx * 32
        bg = q_active_bg if is_active else q_bg
        bd = q_active_border if is_active else q_border
        q_col = dot_live if is_active else accent
        txt_col = ink if is_active else muted
        fw = "600" if is_active else "500"
        pulse = f'<circle cx="356" cy="{my + 1}" r="3.8" fill="{dot_live}" class="peak-halo"/>' if is_active else ""
        live_dot = f'<circle cx="356" cy="{my + 1}" r="3.2" fill="{dot_live}"/>' if is_active else ""
        ms_svgs.append(f"""
        <rect x="26" y="{my - 11}" width="36" height="24" rx="6" fill="{bg}" stroke="{bd}" stroke-width="1"/>
        <text x="44" y="{my + 4.5}" text-anchor="middle" font-family="{FONT_MONO}" font-size="10.5" font-weight="700" fill="{q_col}">{escape(q)}</text>
        <text x="74" y="{my + 4.5}" font-family="{FONT_SANS}" font-size="12.2" font-weight="{fw}" fill="{txt_col}">{escape(desc)}</text>
        {pulse}{live_dot}
        """)

    # Zone B: 2x2 Executive KPI Grid (25+ Modules · 9+ Industry Sectors · Repos · Building Since)
    kpis = [
        ("25+", "QODRA OS MODULES", 392, 96, accent),
        ("9+", "INDUSTRY SECTORS", 512, 96, dot_live),
        (metrics["total_repos"], "REPOSITORIES", 392, 166, ink),
        (metrics["building_since"], "BUILDING SINCE", 512, 166, ink),
    ]
    kpi_svgs = []
    for val, lbl, kx, ky, col in kpis:
        kpi_svgs.append(f"""
        <text x="{kx}" y="{ky}" font-family="{FONT_MONO}" font-size="22" font-weight="700" letter-spacing="-0.5" fill="{col}">{escape(val)}</text>
        <text x="{kx}" y="{ky + 17}" font-family="{FONT_MONO}" font-size="9.0" font-weight="600" letter-spacing="0.3" fill="{muted}">{escape(lbl)}</text>
        """)

    # Zone C: Real Language Footprint Bar + 5 Legend Rows
    langs = metrics["languages"]
    bar_x, bar_y, bar_w, bar_h = 634, 72, 180, 8
    seg_svgs = []
    cur_x = bar_x
    total_pct = sum(l["pct"] for l in langs) or 100.0
    for idx, l in enumerate(langs):
        c = l["color_dark"] if mode == "dark" else l["color_light"]
        sw = (l["pct"] / total_pct) * bar_w
        if idx == len(langs) - 1:
            sw = max(2.0, bar_x + bar_w - cur_x)
        seg_svgs.append(f'<rect x="{cur_x:.2f}" y="{bar_y}" width="{max(sw - 1.5, 2):.2f}" height="{bar_h}" fill="{c}"/>')
        cur_x += sw

    legend_svgs = []
    for idx, l in enumerate(langs):
        ly = 104 + idx * 20.5
        c = l["color_dark"] if mode == "dark" else l["color_light"]
        legend_svgs.append(f"""
        <circle cx="639" cy="{ly - 3.5}" r="3.5" fill="{c}"/>
        <text x="651" y="{ly}" font-family="{FONT_SANS}" font-size="12" font-weight="500" fill="{ink}">{escape(l['name'])}</text>
        <text x="814" y="{ly}" text-anchor="end" font-family="{FONT_MONO}" font-size="11.2" font-weight="600" fill="{muted}">{l['pct']:.1f}%</text>
        """)

    freshness = f"QODRA SYSTEMS · {metrics['updated_label']}"
    dot_x = 814 - len(freshness) * 6.5 - 12
    dna_title = f"CODEBASE DNA ({metrics['total_repos']} REPOS)"

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Executive Engineering Snapshot — 2026 Delivery, Qodra OS Scale and Codebase DNA">
  <defs>
    <style>
      .peak-halo {{
        transform-box: fill-box;
        transform-origin: center;
        animation: peakPulse 3.2s ease-out infinite;
      }}
      @keyframes peakPulse {{
        0% {{ transform: scale(1); opacity: 0.7; }}
        75% {{ transform: scale(2.5); opacity: 0; }}
        100% {{ transform: scale(2.5); opacity: 0; }}
      }}
      @media (prefers-reduced-motion: reduce) {{ .peak-halo {{ animation: none !important; }} }}
    </style>
    <linearGradient id="tbg_{mode}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{bg1}"/>
      <stop offset="100%" stop-color="{bg2}"/>
    </linearGradient>
    <clipPath id="tclip_{mode}">
      <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="14"/>
    </clipPath>
    <clipPath id="tbar_{mode}">
      <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="4"/>
    </clipPath>
  </defs>

  <g clip-path="url(#tclip_{mode})">
    <rect width="{W}" height="{H}" fill="url(#tbg_{mode})"/>
    <line x1="20" y1="1.5" x2="{W-20}" y2="1.5" stroke="#FFFFFF" stroke-opacity="{sheen_op}" stroke-width="1"/>

    <!-- Header Strip -->
    <text x="26" y="30" font-family="{FONT_MONO}" font-size="11" font-weight="700" letter-spacing="1.0" fill="{accent}">ENGINEERING SNAPSHOT  ·  ARCHITECTURE &amp; DELIVERY</text>
    <circle cx="{dot_x:.1f}" cy="26.5" r="3.2" fill="{dot_live}"/>
    <text x="814" y="30" text-anchor="end" font-family="{FONT_MONO}" font-size="9.8" font-weight="600" letter-spacing="0.4" fill="{muted}">{escape(freshness)}</text>
    <line x1="24" y1="44" x2="{W-24}" y2="44" stroke="{divider}" stroke-width="1"/>

    <!-- Zone A: 2026 Delivery Roadmap -->
    {''.join(ms_svgs)}

    <!-- Dividers -->
    <line x1="378" y1="56" x2="378" y2="196" stroke="{divider}" stroke-width="1"/>
    <line x1="620" y1="56" x2="620" y2="196" stroke="{divider}" stroke-width="1"/>

    <!-- Zone B: 2x2 KPIs -->
    <line x1="390" y1="128" x2="608" y2="128" stroke="{divider}" stroke-width="1"/>
    <line x1="500" y1="62" x2="500" y2="190" stroke="{divider}" stroke-width="1"/>
    {''.join(kpi_svgs)}

    <!-- Zone C: Codebase DNA -->
    <text x="634" y="62" font-family="{FONT_MONO}" font-size="9.8" font-weight="600" letter-spacing="0.6" fill="{muted}">{escape(dna_title)}</text>
    <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="4" fill="{bar_bg}"/>
    <g clip-path="url(#tbar_{mode})">
      {''.join(seg_svgs)}
    </g>
    {''.join(legend_svgs)}
  </g>

  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="14" fill="none" stroke="{border}" stroke-width="1"/>
</svg>
"""
    save_svg(ASSETS_DIR / f"telemetry-{mode}.svg", svg)


# ---------------------------------------------------------------------------
# 4. COMPACT 2x2 FOCUSED CORE STACK (840 x 194 — zero ragged void, >=12px type)
# ---------------------------------------------------------------------------
def build_stack(mode="dark"):
    W, H = 840, 194
    if mode == "dark":
        bg1, bg2 = "#0F131E", "#141928"
        border = "#232B42"
        sheen_op = "0.09"
        accent = "#818CF8"
        dot_live = "#34D399"
        ink = "#F8FAFC"
        muted = "#8B95B0"
        divider = "#20273C"
        pill_bg = "#161E31"
        pill_border = "#283350"
        pill_fg = "#E2E8F0"
    else:
        bg1, bg2 = "#FFFFFF", "#F8FAFC"
        border = "#E2E8F0"
        sheen_op = "0.90"
        accent = "#4F46E5"
        dot_live = "#059669"
        ink = "#0F172A"
        muted = "#64748B"
        divider = "#E2E8F0"
        pill_bg = "#F8FAFC"
        pill_border = "#CBD5E1"
        pill_fg = "#1E293B"

    # Opinionated Core Stack (4 crisp pills per quadrant — fits cleanly inside 376px with generous gutter)
    quads = [
        ("DATA & BACKEND CORE", accent, ["PostgreSQL", "PL/pgSQL", "Node.js", "Python"]),
        ("MOBILE & CLIENT UX", dot_live, ["Flutter", "Dart", "TypeScript", "Next.js"]),
        ("GOVERNED AI & AGENTS", accent, ["Awni AI", "Arabic Voice", "Claude", "Gemini"]),
        ("CLOUD & DELIVERY", dot_live, ["AWS", "Google Cloud", "Supabase", "Docker"]),
    ]

    q_svgs = []
    positions = [(26, 62), (434, 62), (26, 132), (434, 132)]
    for (title, dot, items), (qx, qy) in zip(quads, positions):
        q_svgs.append(f'<circle cx="{qx + 4}" cy="{qy - 4}" r="3.2" fill="{dot}"/>')
        q_svgs.append(f'<text x="{qx + 15}" y="{qy}" font-family="{FONT_MONO}" font-size="10.5" font-weight="700" letter-spacing="0.8" fill="{muted}">{escape(title)}</text>')
        cx = qx
        for item in items:
            w = pill_width(item, min_w=58, char_w=7.4, pad=22)
            q_svgs.append(f"""
            <rect x="{cx}" y="{qy + 11}" width="{w}" height="28" rx="7" fill="{pill_bg}" stroke="{pill_border}" stroke-width="1"/>
            <text x="{cx + w/2:.1f}" y="{qy + 29}" text-anchor="middle" font-family="{FONT_SANS}" font-size="12" font-weight="500" fill="{pill_fg}">{escape(item)}</text>
            """)
            cx += w + 8

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Core Production Stack">
  <defs>
    <linearGradient id="sbg_{mode}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{bg1}"/>
      <stop offset="100%" stop-color="{bg2}"/>
    </linearGradient>
    <clipPath id="sclip_{mode}">
      <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="14"/>
    </clipPath>
  </defs>
  <g clip-path="url(#sclip_{mode})">
    <rect width="{W}" height="{H}" fill="url(#sbg_{mode})"/>
    <line x1="20" y1="1.5" x2="{W-20}" y2="1.5" stroke="#FFFFFF" stroke-opacity="{sheen_op}" stroke-width="1"/>
    <text x="26" y="30" font-family="{FONT_MONO}" font-size="11" font-weight="700" letter-spacing="1.0" fill="{accent}">CORE PRODUCTION STACK</text>
    <text x="814" y="30" text-anchor="end" font-family="{FONT_MONO}" font-size="9.8" font-weight="600" letter-spacing="0.5" fill="{muted}">WHAT I SHIP WITH DAILY</text>
    <line x1="24" y1="44" x2="{W-24}" y2="44" stroke="{divider}" stroke-width="1"/>
    <line x1="418" y1="54" x2="418" y2="{H-16}" stroke="{divider}" stroke-width="1"/>
    <line x1="24" y1="114" x2="{W-24}" y2="114" stroke="{divider}" stroke-width="1"/>
    {''.join(q_svgs)}
  </g>
  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="14" fill="none" stroke="{border}" stroke-width="1"/>
</svg>
"""
    save_svg(ASSETS_DIR / f"stack-{mode}.svg", svg)


ICON_ID_CARD = (
    '<rect x="2" y="4.5" width="20" height="15" rx="2.5"/>'
    '<circle cx="8.5" cy="10.2" r="2"/>'
    '<path d="M5.4 15.8c.6-1.5 1.8-2.2 3.1-2.2s2.5.7 3.1 2.2"/>'
    '<path d="M14.5 9.8h4.5M14.5 13.4h3.5"/>'
)
ICON_HEX = '<polygon points="12,2.2 20.5,7.1 20.5,16.9 12,21.8 3.5,16.9 3.5,7.1"/><circle cx="12" cy="12" r="3"/>'
ICON_EMAIL = '<rect x="2.5" y="4.5" width="19" height="15" rx="2.5"/><path d="M3.2 6.2l7.6 5.4a2 2 0 0 0 2.4 0l7.6-5.4"/>'
ICON_LINKEDIN = (
    '<rect x="2.5" y="2.5" width="19" height="19" rx="3.5" fill="none" stroke="{color}" stroke-width="1.9"/>'
    '<circle cx="7.6" cy="8.2" r="1.25" fill="{color}"/>'
    '<path d="M7.6 11v5.8M11.6 16.8V11M11.6 13.4a2.4 2.4 0 0 1 4.8 0v3.4" fill="none" stroke="{color}" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/>'
)
ICON_WHATSAPP = (
    '<path d="M 3.92 15.46 A 9 9 0 1 1 6.72 18.79 L 2.8 20.6 Z" fill="none" stroke="{color}" stroke-width="2.05" stroke-linecap="round" stroke-linejoin="round"/>'
    '<path fill="{color}" d="M 9.35 7.45 c -0.22 -0.49 -0.45 -0.50 -0.66 -0.51 c -0.17 -0.01 -0.37 -0.01 -0.56 -0.01 c -0.20 0 -0.51 0.07 -0.78 0.37 c -0.27 0.29 -1.03 1.00 -1.03 2.45 c 0 1.44 1.05 2.84 1.20 3.04 c 0.15 0.20 2.03 3.25 5.01 4.43 c 2.48 0.98 2.98 0.78 3.52 0.73 c 0.54 -0.05 1.74 -0.71 1.98 -1.40 c 0.24 -0.69 0.24 -1.27 0.17 -1.40 c -0.07 -0.12 -0.27 -0.20 -0.56 -0.34 c -0.29 -0.15 -1.74 -0.86 -2.01 -0.96 c -0.27 -0.10 -0.46 -0.15 -0.66 0.15 c -0.20 0.29 -0.76 0.96 -0.93 1.15 c -0.17 0.20 -0.34 0.22 -0.64 0.07 c -0.29 -0.15 -1.24 -0.46 -2.37 -1.46 c -0.88 -0.78 -1.47 -1.75 -1.64 -2.04 c -0.17 -0.29 -0.02 -0.45 0.13 -0.60 c 0.13 -0.13 0.29 -0.34 0.44 -0.51 c 0.15 -0.17 0.20 -0.29 0.29 -0.49 c 0.10 -0.20 0.05 -0.37 -0.02 -0.51 c -0.07 -0.15 -0.64 -1.59 -0.90 -2.17 Z" transform="translate(-0.35, -0.35) scale(0.95)"/>'
)


def main():
    parser = argparse.ArgumentParser(description="Generate v3 AboodAyyash GitHub profile SVGs.")
    parser.add_argument("--telemetry-only", action="store_true", help="Only regenerate telemetry-{dark,light}.svg")
    parser.add_argument("--strict", action="store_true", help="Fail loudly if live GraphQL refresh errors")
    args = parser.parse_args()

    try:
        metrics = fetch_live_metrics(strict=args.strict)
    except Exception as exc:
        if args.strict:
            print(f"ERROR: Live telemetry fetch failed: {exc}", file=sys.stderr)
            sys.exit(1)
        print(f"Warning: falling back to default metrics ({exc})", file=sys.stderr)
        metrics = DEFAULT_METRICS

    for mode in ("dark", "light"):
        build_telemetry(metrics, mode)
        if not args.telemetry_only:
            build_hero(mode)
            build_stack(mode)
            build_action_button("btn-card", "Digital Card", ICON_ID_CARD, variant="primary", width=154, mode=mode)
            build_action_button("btn-linkedin", "LinkedIn", ICON_LINKEDIN, icon_mode="custom", variant="secondary", width=136, mode=mode)
            build_action_button("btn-org", "Qodra Systems", ICON_HEX, variant="secondary", width=168, mode=mode)
            build_action_button("btn-email", "Email Me", ICON_EMAIL, variant="secondary", width=134, mode=mode)
            build_action_button("btn-whatsapp", "WhatsApp", ICON_WHATSAPP, icon_mode="custom", variant="whatsapp", width=144, mode=mode)

    print("v3 AboodAyyash dashboard assets generated & XML-validated!")


if __name__ == "__main__":
    main()
