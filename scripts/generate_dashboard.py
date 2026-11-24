#!/usr/bin/env python3
"""
Executive GitHub Profile Dashboard Generator — Abd-Alrahman Ayyash (CEO, Qodra Systems)
Generates dual-theme (dark + light) animated, privacy-safe vector SVG dashboard panels.
"""
import json
import math
import os
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

# Verified aggregate baseline from AboodAyyash account (privacy-safe: zero private repo names)
DEFAULT_METRICS = {
    "contributions_12m": "2,610+",
    "total_repos": "32",
    "active_repos_year": "25",
    "building_since": "2018",
    # 12-month trajectory (Dec 2025 -> Nov 2026) normalized shape reflecting real Q4 surge
    "months": ["D", "J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N"],
    "monthly_values": [38, 46, 34, 42, 49, 64, 52, 68, 58, 175, 420, 1564],
    "languages": [
        {"name": "PL/pgSQL", "pct": 39.2, "color_dark": "#60A5FA", "color_light": "#2563EB"},
        {"name": "Dart / Flutter", "pct": 38.1, "color_dark": "#4FBF92", "color_light": "#166549"},
        {"name": "HTML / UI", "pct": 10.8, "color_dark": "#F2A65A", "color_light": "#C2590C"},
        {"name": "JS / TS", "pct": 6.9, "color_dark": "#9A8DF8", "color_light": "#4F46E5"},
        {"name": "Python & Other", "pct": 5.0, "color_dark": "#C084FC", "color_light": "#7E22CE"},
    ],
}


def fetch_live_metrics():
    """Optionally refresh aggregate metrics from GitHub GraphQL when PROFILE_TOKEN is set."""
    token = os.environ.get("PROFILE_TOKEN", "").strip()
    if not token:
        return DEFAULT_METRICS

    query = """
    {
      viewer {
        createdAt
        repositories(first: 100, ownerAffiliations: OWNER) {
          totalCount
          nodes {
            languages(first: 8, orderBy: {field: SIZE, direction: DESC}) {
              edges { size node { name } }
            }
          }
        }
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks { contributionDays { date contributionCount } }
          }
        }
      }
    }
    """
    try:
        req = urllib.request.Request(
            "https://api.github.com/graphql",
            data=json.dumps({"query": query}).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "AboodAyyash-Profile-Generator",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        viewer = payload["data"]["viewer"]
        cal = viewer["contributionsCollection"]["contributionCalendar"]
        total_contrib = cal["totalContributions"]
        if total_contrib < 50:
            # Token lacks private contribution visibility; keep verified baseline
            return DEFAULT_METRICS

        days = [d for w in cal["weeks"] for d in w["contributionDays"]]
        monthly = defaultdict(int)
        for d in days:
            monthly[d["date"][:7]] += d["contributionCount"]
        sorted_months = sorted(monthly.items())[-12:]
        month_letters = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]
        months = [month_letters[int(ym.split("-")[1]) - 1] for ym, _ in sorted_months]
        vals = [v for _, v in sorted_months]

        langs = defaultdict(int)
        for r in viewer["repositories"]["nodes"]:
            for e in r["languages"]["edges"]:
                langs[e["node"]["name"]] += e["size"]
        total_bytes = sum(langs.values()) or 1

        # Group cleanly into top 4 + Other
        grouped = defaultdict(int)
        for k, v in langs.items():
            if k == "PLpgSQL":
                grouped["PL/pgSQL"] += v
            elif k == "Dart":
                grouped["Dart / Flutter"] += v
            elif k in ("JavaScript", "TypeScript"):
                grouped["JS / TS"] += v
            elif k in ("HTML", "CSS"):
                grouped["HTML / UI"] += v
            else:
                grouped["Python & Other"] += v

        palette = {
            "PL/pgSQL": ("#60A5FA", "#2563EB"),
            "Dart / Flutter": ("#4FBF92", "#166549"),
            "HTML / UI": ("#F2A65A", "#C2590C"),
            "JS / TS": ("#9A8DF8", "#4F46E5"),
            "Python & Other": ("#C084FC", "#7E22CE"),
        }
        top_langs = []
        for name, size in sorted(grouped.items(), key=lambda x: -x[1])[:5]:
            cd, cl = palette.get(name, ("#94A3B8", "#475569"))
            top_langs.append({"name": name, "pct": round(size * 100.0 / total_bytes, 1), "color_dark": cd, "color_light": cl})

        metrics = dict(DEFAULT_METRICS)
        metrics["contributions_12m"] = f"{total_contrib:,}"
        metrics["total_repos"] = str(viewer["repositories"]["totalCount"])
        metrics["building_since"] = viewer["createdAt"][:4]
        if len(months) == 12:
            metrics["months"] = months
            metrics["monthly_values"] = vals
        if top_langs:
            metrics["languages"] = top_langs
        return metrics
    except Exception:
        return DEFAULT_METRICS


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


def pill_width(label: str, min_w=56, char_w=7.5, pad=24):
    return max(min_w, int(round(len(label) * char_w + pad)))


def qodra_logo_group(tx, ty, scale, mode="dark", uid="q"):
    if mode == "dark":
        c0a, c0b = "#3B82F6", "#2563EB"
        c1a, c1b = "#818CF8", "#4F46E5"
        c2a, c2b = "#60A5FA", "#3B82F6"
    else:
        c0a, c0b = "#2563EB", "#1D4ED8"
        c1a, c1b = "#4F46E5", "#3730A3"
        c2a, c2b = "#3B82F6", "#2563EB"

    defs = f"""
    <linearGradient id="{uid}_b0" gradientUnits="userSpaceOnUse" x1="69.92" y1="-136.42" x2="134.28" y2="73.96">
      <stop offset="0" stop-color="{c0a}"/><stop offset="1" stop-color="{c0b}"/>
    </linearGradient>
    <linearGradient id="{uid}_b1" gradientUnits="userSpaceOnUse" x1="83.19" y1="128.76" x2="-131.19" y2="79.31">
      <stop offset="0" stop-color="{c1a}"/><stop offset="1" stop-color="{c1b}"/>
    </linearGradient>
    <linearGradient id="{uid}_b2" gradientUnits="userSpaceOnUse" x1="-153.11" y1="7.66" x2="-3.09" y2="-153.27">
      <stop offset="0" stop-color="{c2a}"/><stop offset="1" stop-color="{c2b}"/>
    </linearGradient>
    """
    paths = f"""
    <g transform="translate({tx},{ty}) scale({scale})">
      <path d="M 178.00 0.00 L 123.50 94.40 L 60.00 57.74 L 60.00 -154.15 L 89.00 -154.15 Z" fill="url(#{uid}_b0)" stroke="url(#{uid}_b0)" stroke-width="10" stroke-linejoin="round"/>
      <path d="M 103.50 129.04 L 89.00 154.15 L -89.00 154.15 L -143.50 59.76 L -80.00 23.09 Z" fill="url(#{uid}_b1)" stroke="url(#{uid}_b1)" stroke-width="10" stroke-linejoin="round"/>
      <path d="M -163.50 25.11 L -178.00 0.00 L -89.00 -154.15 L 20.00 -154.15 L 20.00 -80.83 Z" fill="url(#{uid}_b2)" stroke="url(#{uid}_b2)" stroke-width="10" stroke-linejoin="round"/>
    </g>
    """
    return defs, paths


def smooth_curve_path(points):
    """Generate smooth cubic Bezier SVG path through (x, y) tuples."""
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
        # Clamp Y to stay inside chart bounds smoothly
        min_y = min(p1[1], p2[1]) - 6
        max_y = max(p1[1], p2[1]) + 6
        cp1y = max(min_y, min(max_y, cp1y))
        cp2y = max(min_y, min(max_y, cp2y))
        d.append(f"C {cp1x:.2f} {cp1y:.2f}, {cp2x:.2f} {cp2y:.2f}, {p2[0]:.2f} {p2[1]:.2f}")
    return " ".join(d)


# ---------------------------------------------------------------------------
# 1. LIVING ARCHITECTURAL HERO (840 x 272)
# ---------------------------------------------------------------------------
def build_hero(mode="dark"):
    W, H = 840, 272
    if mode == "dark":
        bg1, bg2 = "#111026", "#181634"
        border = "#2F2C52"
        sheen_op = "0.14"
        ink = "#F6F4FF"
        sub_accent = "#A296FA"
        muted = "#BCB8D4"
        pill_bg = "#1D1B38"
        pill_border = "#35315E"
        badge_bg = "#201D40"
        badge_border = "#3E3972"
        hex_stroke = "#3A3666"
        center_hex_fill = "#111024"
        center_hex_stroke = "#655DF0"
        glow_color = "#5A52EA"
        glow_opacity = "0.32"
        dot_color = "#4FBF92"
        chip_text = "#DCD7FF"
        grid_dot = "#9A8DF8"
        grid_op = "0.10"
        pulse_color = "#A5B4FC"
    else:
        bg1, bg2 = "#FCFBF8", "#F3F0E8"
        border = "#DDD8CE"
        sheen_op = "0.90"
        ink = "#17162B"
        sub_accent = "#4338CA"
        muted = "#4D4A61"
        pill_bg = "#FFFFFF"
        pill_border = "#DDD8CE"
        badge_bg = "#EBE9FE"
        badge_border = "#C7C2FA"
        hex_stroke = "#CFC9E6"
        center_hex_fill = "#1B1A33"
        center_hex_stroke = "#4F46E5"
        glow_color = "#4F46E5"
        glow_opacity = "0.13"
        dot_color = "#166549"
        chip_text = "#312E81"
        grid_dot = "#4F46E5"
        grid_op = "0.09"
        pulse_color = "#4F46E5"

    cx, cy = 694, 136
    r_center = 40
    ring_dist = 76
    r_sat = 29

    satellites = [
        (0, "AI", "#5A52EA" if mode == "dark" else "#4338CA", "3.6s", "0s"),
        (60, "ERP", "#2E7564" if mode == "dark" else "#166549", "4.2s", "0.7s"),
        (120, "POS", "#9C5B82" if mode == "dark" else "#8A4570", "3.9s", "1.4s"),
        (180, "NAV", "#8B5CF6" if mode == "dark" else "#6D28D9", "4.5s", "2.1s"),
        (240, "CLOUD", "#3B82F6" if mode == "dark" else "#1D4ED8", "3.8s", "2.8s"),
        (300, "HR", "#C89B3C" if mode == "dark" else "#9A6B16", "4.4s", "3.5s"),
    ]

    sat_svgs = []
    # Faint orbital blueprint ring
    sat_svgs.append(
        f'<circle cx="{cx}" cy="{cy}" r="{ring_dist}" fill="none" stroke="{hex_stroke}" stroke-opacity="0.40" stroke-width="1" stroke-dasharray="3 5"/>'
    )
    for deg in range(30, 360, 60):
        rad = math.radians(deg)
        ox = cx + 138 * math.cos(rad)
        oy = cy + 138 * math.sin(rad)
        sat_svgs.append(
            f'<polygon points="{hex_points(ox, oy, 26, True)}" fill="none" stroke="{hex_stroke}" stroke-opacity="0.28" stroke-width="1"/>'
        )

    for idx, (deg, label, tint, dur, begin) in enumerate(satellites):
        rad = math.radians(deg - 30)
        sx = cx + ring_dist * math.cos(rad)
        sy = cy + ring_dist * math.sin(rad)
        # Edge-to-edge spoke path for smooth SMIL pulse packet
        x1 = cx + (r_center + 2) * math.cos(rad)
        y1 = cy + (r_center + 2) * math.sin(rad)
        x2 = sx - (r_sat + 1) * math.cos(rad)
        y2 = sy - (r_sat + 1) * math.sin(rad)
        sat_svgs.append(
            f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{sx:.1f}" y2="{sy:.1f}" stroke="{hex_stroke}" stroke-opacity="0.65" stroke-width="1.1"/>'
        )
        # Living telemetry packet along spoke
        sat_svgs.append(f"""
        <circle r="2.2" fill="{pulse_color}" opacity="0">
          <animateMotion dur="{dur}" begin="{begin}" repeatCount="indefinite" path="M {x1:.1f} {y1:.1f} L {x2:.1f} {y2:.1f}"/>
          <animate attributeName="opacity" values="0;0.95;0.95;0" keyTimes="0;0.18;0.82;1" dur="{dur}" begin="{begin}" repeatCount="indefinite"/>
        </circle>
        """)
        fill_op = "0.22" if mode == "dark" else "0.10"
        stroke_op = "0.58" if mode == "dark" else "0.38"
        sat_svgs.append(
            f'<polygon points="{hex_points(sx, sy, r_sat, True)}" fill="{tint}" fill-opacity="{fill_op}" stroke="{tint}" stroke-opacity="{stroke_op}" stroke-width="1.2"/>'
        )
        sat_svgs.append(
            f'<text x="{sx:.1f}" y="{sy + 3.8:.1f}" text-anchor="middle" font-family="{FONT_MONO}" font-size="9.5" font-weight="700" letter-spacing="0.6" fill="{ink if mode == "dark" else tint}" fill-opacity="0.94">{escape(label)}</text>'
        )

    logo_defs, logo_paths = qodra_logo_group(cx, cy, 0.132, mode="dark", uid=f"hero_{mode}")

    # Metadata chips with mini inline icons
    chips = [
        ("Amman, Jordan", 34, 140, '<path d="M6 11s3.5-3.1 3.5-5.8a3.5 3.5 0 1 0-7 0C2.5 7.9 6 11 6 11z"/><circle cx="6" cy="5.2" r="1.2"/>'),
        ("qodrasystems.com", 184, 160, '<circle cx="6" cy="6" r="4.6"/><path d="M1.4 6h9.2M6 1.4a7 7 0 0 1 0 9.2 7 7 0 0 1 0-9.2z"/>'),
        ("MENA Enterprise SaaS", 354, 178, '<path d="M6 1.3L1.5 3.8v4.4L6 10.7l4.5-2.5V3.8L6 1.3z"/><path d="M1.5 3.8L6 6.3l4.5-2.5M6 6.3v4.4"/>'),
    ]
    chip_svgs = []
    for text, x, w, icon in chips:
        chip_svgs.append(f"""
        <rect x="{x}" y="206" width="{w}" height="30" rx="8" fill="{pill_bg}" stroke="{pill_border}" stroke-width="1"/>
        <g transform="translate({x + 11}, 215)" fill="none" stroke="{sub_accent}" stroke-width="1.35" stroke-linecap="round" stroke-linejoin="round">{icon}</g>
        <text x="{x + 29}" y="225.2" font-family="{FONT_SANS}" font-size="11.8" font-weight="500" fill="{chip_text}">{escape(text)}</text>
        """)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Abd-Alrahman Ayyash — CEO at Qodra Systems">
  <defs>
    <style>
      .beacon-ring {{
        transform-box: fill-box;
        transform-origin: center;
        animation: beacon 2.8s cubic-bezier(0.2, 0.7, 0.3, 1) infinite;
      }}
      .core-glow {{
        animation: breathe 4.6s ease-in-out infinite;
      }}
      @keyframes beacon {{
        0% {{ transform: scale(1); opacity: 0.72; }}
        70% {{ transform: scale(2.4); opacity: 0; }}
        100% {{ transform: scale(2.4); opacity: 0; }}
      }}
      @keyframes breathe {{
        0%, 100% {{ opacity: 0.78; }}
        50% {{ opacity: 1; }}
      }}
      @media (prefers-reduced-motion: reduce) {{
        .beacon-ring, .core-glow {{ animation: none !important; }}
      }}
    </style>
    <linearGradient id="bg_{mode}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{bg1}"/>
      <stop offset="100%" stop-color="{bg2}"/>
    </linearGradient>
    <radialGradient id="glow_{mode}" cx="82%" cy="50%" r="42%">
      <stop offset="0%" stop-color="{glow_color}" stop-opacity="{glow_opacity}"/>
      <stop offset="100%" stop-color="{glow_color}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="sheen_{mode}" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#FFFFFF" stop-opacity="0"/>
      <stop offset="30%" stop-color="#FFFFFF" stop-opacity="{sheen_op}"/>
      <stop offset="70%" stop-color="#FFFFFF" stop-opacity="{sheen_op}"/>
      <stop offset="100%" stop-color="#FFFFFF" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="top_accent_{mode}" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#4F46E5" stop-opacity="0"/>
      <stop offset="26%" stop-color="#6366F1" stop-opacity="0.92"/>
      <stop offset="74%" stop-color="#A5B4FC" stop-opacity="0.92"/>
      <stop offset="100%" stop-color="#4F46E5" stop-opacity="0"/>
    </linearGradient>
    <pattern id="dots_{mode}" x="0" y="0" width="22" height="22" patternUnits="userSpaceOnUse">
      <circle cx="2" cy="2" r="1" fill="{grid_dot}" fill-opacity="{grid_op}"/>
    </pattern>
    <linearGradient id="dot_fade_{mode}" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="40%" stop-color="#FFFFFF" stop-opacity="0"/>
      <stop offset="78%" stop-color="#FFFFFF" stop-opacity="1"/>
      <stop offset="100%" stop-color="#FFFFFF" stop-opacity="0.6"/>
    </linearGradient>
    <mask id="dot_mask_{mode}">
      <rect width="{W}" height="{H}" fill="url(#dot_fade_{mode})"/>
    </mask>
    <clipPath id="clip_{mode}">
      <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="16"/>
    </clipPath>
    {logo_defs}
  </defs>

  <g clip-path="url(#clip_{mode})">
    <rect width="{W}" height="{H}" fill="url(#bg_{mode})"/>
    <rect width="{W}" height="{H}" fill="url(#dots_{mode})" mask="url(#dot_mask_{mode})"/>
    <rect width="{W}" height="{H}" fill="url(#glow_{mode})" class="core-glow"/>
    <rect x="0" y="0" width="{W}" height="2.5" fill="url(#top_accent_{mode})"/>
    <rect x="0" y="2.5" width="{W}" height="1" fill="url(#sheen_{mode})"/>

    <!-- Living Qodra Constellation -->
    {''.join(sat_svgs)}
    <polygon points="{hex_points(cx, cy, r_center + 6, True)}" fill="none" stroke="{center_hex_stroke}" stroke-opacity="0.32" stroke-width="1"/>
    <polygon points="{hex_points(cx, cy, r_center, True)}" fill="{center_hex_fill}" stroke="{center_hex_stroke}" stroke-width="1.8"/>
    {logo_paths}

    <!-- Left Content -->
    <rect x="34" y="34" width="218" height="28" rx="14" fill="{badge_bg}" stroke="{badge_border}" stroke-width="1"/>
    <circle cx="50" cy="48" r="4" fill="{dot_color}" class="beacon-ring"/>
    <circle cx="50" cy="48" r="3.8" fill="{dot_color}"/>
    <text x="63" y="52.2" font-family="{FONT_MONO}" font-size="11" font-weight="700" letter-spacing="1.0" fill="{sub_accent}">CEO · QODRA SYSTEMS</text>

    <text x="34" y="104" font-family="{FONT_SANS}" font-size="34" font-weight="700" letter-spacing="-0.7" fill="{ink}">Abd-Alrahman Ayyash</text>

    <text x="34" y="131" font-family="{FONT_SANS}" font-size="14.2" font-weight="600" fill="{sub_accent}">Chief Executive Officer  ·  Founder &amp; Systems Architect</text>

    <text x="34" y="161" font-family="{FONT_SANS}" font-size="13.5" font-weight="400" fill="{muted}">Building unified business operating systems, permission-aware AI agents,</text>
    <text x="34" y="182" font-family="{FONT_SANS}" font-size="13.5" font-weight="400" fill="{muted}">indoor navigation platforms, and custom software for modern enterprises.</text>

    {''.join(chip_svgs)}
  </g>

  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="16" fill="none" stroke="{border}" stroke-width="1"/>
</svg>
"""
    save_svg(ASSETS_DIR / f"hero-{mode}.svg", svg)


# ---------------------------------------------------------------------------
# 2. PRECISION EXECUTIVE CTA BUTTONS (height=40, authentic 24x24 icons)
# ---------------------------------------------------------------------------
def build_action_button(filename, label, icon_markup, icon_mode="stroke", variant="secondary", width=184, mode="dark"):
    H = 40
    if variant == "primary":
        bg1 = "#625AF2" if mode == "dark" else "#4F46E5"
        bg2 = "#4D45DC" if mode == "dark" else "#4338CA"
        border = "#837CF8" if mode == "dark" else "#3730A3"
        fg = "#FFFFFF"
        icon_color = "#FFFFFF"
        sheen_op = "0.24"
    elif variant == "whatsapp":
        bg1 = "#112E24" if mode == "dark" else "#E8F8F0"
        bg2 = "#0E251D" if mode == "dark" else "#DCF4E8"
        border = "#24664D" if mode == "dark" else "#9CDAB9"
        fg = "#6EE7B7" if mode == "dark" else "#166549"
        icon_color = "#25D366" if mode == "dark" else "#16A34A"
        sheen_op = "0.10"
    else:
        bg1 = "#191830" if mode == "dark" else "#FDFCFA"
        bg2 = "#141326" if mode == "dark" else "#F4F1EA"
        border = "#322E56" if mode == "dark" else "#DDD8CE"
        fg = "#EEEBFF" if mode == "dark" else "#17162B"
        icon_color = "#A296FA" if mode == "dark" else "#4338CA"
        sheen_op = "0.10" if mode == "dark" else "0.80"

    text_w = len(label) * 7.4
    group_w = 17 + 9 + text_w
    start_x = max(14, (width - group_w) / 2.0)

    if icon_mode == "fill":
        icon_group = f'<g transform="translate({start_x:.1f}, 11.5) scale(0.71)" fill="{icon_color}">{icon_markup}</g>'
    else:
        icon_group = f'<g transform="translate({start_x:.1f}, 11.5) scale(0.71)" fill="none" stroke="{icon_color}" stroke-width="1.95" stroke-linecap="round" stroke-linejoin="round">{icon_markup}</g>'

    shimmer_css = ""
    shimmer_rect = ""
    if variant == "primary":
        shimmer_css = """
        <style>
          .shimmer { animation: sweep 6.5s ease-in-out infinite; }
          @keyframes sweep {
            0%, 62% { transform: translateX(-120px); opacity: 0; }
            72% { opacity: 0.24; }
            96% { transform: translateX(260px); opacity: 0; }
            100% { transform: translateX(260px); opacity: 0; }
          }
          @media (prefers-reduced-motion: reduce) { .shimmer { animation: none !important; opacity: 0; } }
        </style>
        """
        shimmer_rect = f'<polygon class="shimmer" points="0,0 38,0 18,{H} -20,{H}" fill="#FFFFFF" opacity="0"/>'

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{H}" viewBox="0 0 {width} {H}" role="img" aria-label="{escape(label)}">
  <defs>
    {shimmer_css}
    <linearGradient id="btn_{filename}_{mode}" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="{bg1}"/>
      <stop offset="100%" stop-color="{bg2}"/>
    </linearGradient>
    <clipPath id="btn_clip_{filename}_{mode}">
      <rect x="0.5" y="0.5" width="{width-1}" height="{H-1}" rx="10"/>
    </clipPath>
  </defs>
  <g clip-path="url(#btn_clip_{filename}_{mode})">
    <rect width="{width}" height="{H}" fill="url(#btn_{filename}_{mode})"/>
    <line x1="12" y1="1.5" x2="{width-12}" y2="1.5" stroke="#FFFFFF" stroke-opacity="{sheen_op}" stroke-width="1"/>
    {shimmer_rect}
    {icon_group}
    <text x="{start_x + 25:.1f}" y="24.5" font-family="{FONT_SANS}" font-size="13" font-weight="600" fill="{fg}">{escape(label)}</text>
  </g>
  <rect x="0.5" y="0.5" width="{width-1}" height="{H-1}" rx="10" fill="none" stroke="{border}" stroke-width="1"/>
</svg>
"""
    save_svg(ASSETS_DIR / f"{filename}-{mode}.svg", svg)


# ---------------------------------------------------------------------------
# 3. EXECUTIVE ENGINEERING TELEMETRY PANEL (840 x 216, privacy-safe)
# ---------------------------------------------------------------------------
def build_telemetry(metrics, mode="dark"):
    W, H = 840, 216
    if mode == "dark":
        bg1, bg2 = "#131227", "#181632"
        border = "#2E2B50"
        sheen_op = "0.11"
        header_fg = "#A296FA"
        ink = "#F6F4FF"
        muted = "#9B96B8"
        grid_line = "#262344"
        divider = "#29264A"
        curve_stroke = "#8B80FA"
        curve_fill_top = "#6366F1"
        dot_live = "#4FBF92"
        bar_bg = "#211E3D"
    else:
        bg1, bg2 = "#FCFBF8", "#F5F2EB"
        border = "#DDD8CE"
        sheen_op = "0.85"
        header_fg = "#4338CA"
        ink = "#17162B"
        muted = "#66627D"
        grid_line = "#E6E1D8"
        divider = "#E2DDD4"
        curve_stroke = "#4F46E5"
        curve_fill_top = "#4F46E5"
        dot_live = "#166549"
        bar_bg = "#E8E4DC"

    # Zone A: 12-Month Velocity Curve (x=28..362, y=74..172)
    vals = metrics["monthly_values"]
    months = metrics["months"]
    # Use log-blended scaling so early months stay visible while Q4 surge looks dramatic & accurate
    scaled = [math.pow(max(v, 1), 0.45) for v in vals]
    max_s = max(scaled) or 1.0
    min_s = min(scaled)

    x_start, x_end = 28.0, 360.0
    y_top, y_bot = 74.0, 172.0
    step_x = (x_end - x_start) / (len(vals) - 1)

    pts = []
    for i, sv in enumerate(scaled):
        norm = (sv - min_s * 0.65) / max(max_s - min_s * 0.65, 1e-6)
        x = x_start + i * step_x
        y = y_bot - norm * (y_bot - y_top)
        pts.append((x, y))

    curve_d = smooth_curve_path(pts)
    area_d = f"{curve_d} L {pts[-1][0]:.2f} {y_bot:.2f} L {pts[0][0]:.2f} {y_bot:.2f} Z"
    last_x, last_y = pts[-1]

    month_labels = []
    for i, m in enumerate(months):
        mx = x_start + i * step_x
        col = header_fg if i == len(months) - 1 else muted
        fw = "700" if i == len(months) - 1 else "500"
        month_labels.append(
            f'<text x="{mx:.1f}" y="192" text-anchor="middle" font-family="{FONT_MONO}" font-size="10" font-weight="{fw}" fill="{col}">{escape(m)}</text>'
        )

    # Zone B: 2x2 Executive KPI Grid (x=384..612, generous 110px columns)
    kpis = [
        (metrics["contributions_12m"], "12M ACTIVITY", 398, 96, header_fg),
        (metrics["total_repos"], "REPOSITORIES", 514, 96, ink),
        (metrics["active_repos_year"], "ACTIVE IN 2026", 398, 166, dot_live),
        (metrics["building_since"], "BUILDING SINCE", 514, 166, ink),
    ]
    kpi_svgs = []
    for val, lbl, kx, ky, col in kpis:
        kpi_svgs.append(f"""
        <text x="{kx}" y="{ky}" font-family="{FONT_MONO}" font-size="21" font-weight="700" letter-spacing="-0.5" fill="{col}">{escape(val)}</text>
        <text x="{kx}" y="{ky + 17}" font-family="{FONT_MONO}" font-size="8.8" font-weight="600" letter-spacing="0.5" fill="{muted}">{escape(lbl)}</text>
        """)

    # Zone C: Language Footprint Bar + 5 Legend Rows (x=632..814)
    langs = metrics["languages"]
    bar_x, bar_y, bar_w, bar_h = 632, 70, 182, 8
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
        ly = 102 + idx * 21
        c = l["color_dark"] if mode == "dark" else l["color_light"]
        legend_svgs.append(f"""
        <circle cx="635" cy="{ly - 3.5}" r="3.5" fill="{c}"/>
        <text x="646" y="{ly}" font-family="{FONT_SANS}" font-size="11.5" font-weight="500" fill="{ink}">{escape(l['name'])}</text>
        <text x="814" y="{ly}" text-anchor="end" font-family="{FONT_MONO}" font-size="11" font-weight="600" fill="{muted}">{l['pct']:.1f}%</text>
        """)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Engineering Telemetry and 12-Month Velocity">
  <defs>
    <style>
      .peak-halo {{
        transform-box: fill-box;
        transform-origin: center;
        animation: peakPulse 3s ease-out infinite;
      }}
      @keyframes peakPulse {{
        0% {{ transform: scale(1); opacity: 0.7; }}
        75% {{ transform: scale(2.6); opacity: 0; }}
        100% {{ transform: scale(2.6); opacity: 0; }}
      }}
      @media (prefers-reduced-motion: reduce) {{ .peak-halo {{ animation: none !important; }} }}
    </style>
    <linearGradient id="tel_bg_{mode}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{bg1}"/>
      <stop offset="100%" stop-color="{bg2}"/>
    </linearGradient>
    <linearGradient id="area_{mode}" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="{curve_fill_top}" stop-opacity="0.34"/>
      <stop offset="100%" stop-color="{curve_fill_top}" stop-opacity="0.01"/>
    </linearGradient>
    <clipPath id="tel_clip_{mode}">
      <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="14"/>
    </clipPath>
    <clipPath id="bar_clip_{mode}">
      <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="4"/>
    </clipPath>
  </defs>

  <g clip-path="url(#tel_clip_{mode})">
    <rect width="{W}" height="{H}" fill="url(#tel_bg_{mode})"/>
    <line x1="20" y1="1.5" x2="{W-20}" y2="1.5" stroke="#FFFFFF" stroke-opacity="{sheen_op}" stroke-width="1"/>

    <!-- Header Strip -->
    <text x="26" y="30" font-family="{FONT_MONO}" font-size="11" font-weight="700" letter-spacing="1.1" fill="{header_fg}">ENGINEERING TELEMETRY  ·  12-MONTH VELOCITY</text>
    <circle cx="640" cy="26.5" r="3.2" fill="{dot_live}"/>
    <text x="650" y="30" font-family="{FONT_MONO}" font-size="9.5" font-weight="600" letter-spacing="0.6" fill="{muted}">PRIVATE + PUBLIC AGGREGATED</text>
    <line x1="24" y1="44" x2="{W-24}" y2="44" stroke="{divider}" stroke-width="1"/>

    <!-- Zone A: Velocity Chart -->
    <line x1="26" y1="74" x2="364" y2="74" stroke="{grid_line}" stroke-width="1" stroke-dasharray="2 4"/>
    <line x1="26" y1="123" x2="364" y2="123" stroke="{grid_line}" stroke-width="1" stroke-dasharray="2 4"/>
    <line x1="26" y1="172" x2="364" y2="172" stroke="{grid_line}" stroke-width="1"/>

    <path d="{area_d}" fill="url(#area_{mode})"/>
    <path d="{curve_d}" fill="none" stroke="{curve_stroke}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="{last_x:.2f}" cy="{last_y:.2f}" r="4.5" fill="{dot_live}" class="peak-halo"/>
    <circle cx="{last_x:.2f}" cy="{last_y:.2f}" r="4" fill="{dot_live}" stroke="{bg1}" stroke-width="1.5"/>
    {''.join(month_labels)}

    <!-- Vertical Zone Dividers -->
    <line x1="382" y1="56" x2="382" y2="196" stroke="{divider}" stroke-width="1"/>
    <line x1="614" y1="56" x2="614" y2="196" stroke="{divider}" stroke-width="1"/>

    <!-- Zone B: 2x2 KPIs -->
    <line x1="396" y1="128" x2="600" y2="128" stroke="{divider}" stroke-width="1"/>
    <line x1="498" y1="62" x2="498" y2="190" stroke="{divider}" stroke-width="1"/>
    {''.join(kpi_svgs)}

    <!-- Zone C: Codebase DNA -->
    <text x="632" y="61" font-family="{FONT_MONO}" font-size="9.5" font-weight="600" letter-spacing="0.8" fill="{muted}">CODEBASE DNA (32 REPOS)</text>
    <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="4" fill="{bar_bg}"/>
    <g clip-path="url(#bar_clip_{mode})">
      {''.join(seg_svgs)}
    </g>
    {''.join(legend_svgs)}
  </g>

  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="14" fill="none" stroke="{border}" stroke-width="1"/>
</svg>
"""
    save_svg(ASSETS_DIR / f"telemetry-{mode}.svg", svg)


# ---------------------------------------------------------------------------
# 4. UPGRADED FLAGSHIP PRODUCT BENTO CARDS (414 x 192, unique micro-visuals)
# ---------------------------------------------------------------------------
def build_product_card(filename, title, subtitle, line1, line2, tags, accent_dark, accent_light, icon_svg, micro_visual, mode="dark"):
    W, H = 414, 192
    if mode == "dark":
        bg1, bg2 = "#131227", "#181632"
        border = "#2E2B50"
        sheen_op = "0.10"
        ink = "#F6F4FF"
        muted = "#B7B3CE"
        tag_bg = "#1E1C3A"
        tag_border = "#35315E"
        tag_fg = "#D6D1FF"
        accent = accent_dark
        icon_bg_op = "0.16"
        arrow_bg = "#1E1C3A"
        arrow_border = "#35315E"
        arrow_fg = "#B7B3CE"
    else:
        bg1, bg2 = "#FCFBF8", "#F4F1EA"
        border = "#DDD8CE"
        sheen_op = "0.85"
        ink = "#17162B"
        muted = "#524F66"
        tag_bg = "#FFFFFF"
        tag_border = "#DDD8CE"
        tag_fg = "#35324A"
        accent = accent_light
        icon_bg_op = "0.11"
        arrow_bg = "#FFFFFF"
        arrow_border = "#DDD8CE"
        arrow_fg = "#524F66"

    tag_svgs = []
    tx = 22
    for t in tags:
        tw = pill_width(t, min_w=46, char_w=6.8, pad=18)
        tag_svgs.append(f"""
        <rect x="{tx}" y="146" width="{tw}" height="26" rx="7" fill="{tag_bg}" stroke="{tag_border}" stroke-width="1"/>
        <text x="{tx + tw/2:.1f}" y="163" text-anchor="middle" font-family="{FONT_SANS}" font-size="11" font-weight="500" fill="{tag_fg}">{escape(t)}</text>
        """)
        tx += tw + 7

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{escape(title)}">
  <defs>
    <linearGradient id="cbg_{filename}_{mode}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{bg1}"/>
      <stop offset="100%" stop-color="{bg2}"/>
    </linearGradient>
    <linearGradient id="ctop_{filename}_{mode}" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{accent}" stop-opacity="0"/>
      <stop offset="22%" stop-color="{accent}" stop-opacity="0.9"/>
      <stop offset="78%" stop-color="{accent}" stop-opacity="0.9"/>
      <stop offset="100%" stop-color="{accent}" stop-opacity="0"/>
    </linearGradient>
    <radialGradient id="cglow_{filename}_{mode}" cx="11%" cy="22%" r="36%">
      <stop offset="0%" stop-color="{accent}" stop-opacity="{0.22 if mode == 'dark' else 0.11}"/>
      <stop offset="100%" stop-color="{accent}" stop-opacity="0"/>
    </radialGradient>
    <clipPath id="cclip_{filename}_{mode}">
      <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="14"/>
    </clipPath>
  </defs>

  <g clip-path="url(#cclip_{filename}_{mode})">
    <rect width="{W}" height="{H}" fill="url(#cbg_{filename}_{mode})"/>
    <rect width="{W}" height="{H}" fill="url(#cglow_{filename}_{mode})"/>
    <rect x="0" y="0" width="{W}" height="2.5" fill="url(#ctop_{filename}_{mode})"/>
    <line x1="16" y1="2.5" x2="{W-16}" y2="2.5" stroke="#FFFFFF" stroke-opacity="{sheen_op}" stroke-width="1"/>

    <!-- Subtle Domain Micro-Visual (right accent) -->
    {micro_visual(accent, mode)}

    <!-- Hex Icon Badge -->
    <polygon points="{hex_points(42, 44, 20, True)}" fill="{accent}" fill-opacity="{icon_bg_op}" stroke="{accent}" stroke-opacity="0.5" stroke-width="1.2"/>
    <g transform="translate(33, 35)" fill="none" stroke="{accent}" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
      {icon_svg}
    </g>

    <!-- Title & Subtitle -->
    <text x="74" y="40" font-family="{FONT_SANS}" font-size="16" font-weight="700" fill="{ink}">{escape(title)}</text>
    <text x="74" y="58" font-family="{FONT_MONO}" font-size="10.2" font-weight="700" letter-spacing="0.5" fill="{accent}">{escape(subtitle)}</text>

    <!-- Clickable Arrow Pill -->
    <rect x="{W - 44}" y="22" width="24" height="24" rx="7" fill="{arrow_bg}" stroke="{arrow_border}" stroke-width="1"/>
    <g transform="translate({W - 40}, 26)" fill="none" stroke="{arrow_fg}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
      <path d="M5 11L11 5M6 5h5v5"/>
    </g>

    <!-- Description -->
    <text x="22" y="98" font-family="{FONT_SANS}" font-size="12.6" fill="{muted}">{escape(line1)}</text>
    <text x="22" y="118" font-family="{FONT_SANS}" font-size="12.6" fill="{muted}">{escape(line2)}</text>

    <!-- Tags -->
    {''.join(tag_svgs)}
  </g>

  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="14" fill="none" stroke="{border}" stroke-width="1"/>
</svg>
"""
    save_svg(ASSETS_DIR / f"{filename}-{mode}.svg", svg)


def micro_erp(accent, mode):
    op = "0.28" if mode == "dark" else "0.18"
    return f"""
    <g transform="translate(332, 130)" opacity="0.88">
      <rect x="0" y="22" width="9" height="18" rx="2.5" fill="{accent}" fill-opacity="{op}">
        <animate attributeName="opacity" values="0.5;1;0.5" dur="3.2s" begin="0s" repeatCount="indefinite"/>
      </rect>
      <rect x="14" y="14" width="9" height="26" rx="2.5" fill="{accent}" fill-opacity="{op}">
        <animate attributeName="opacity" values="0.5;1;0.5" dur="3.2s" begin="0.6s" repeatCount="indefinite"/>
      </rect>
      <rect x="28" y="18" width="9" height="22" rx="2.5" fill="{accent}" fill-opacity="{op}">
        <animate attributeName="opacity" values="0.5;1;0.5" dur="3.2s" begin="1.2s" repeatCount="indefinite"/>
      </rect>
      <rect x="42" y="4" width="9" height="36" rx="2.5" fill="{accent}" fill-opacity="0.58">
        <animate attributeName="opacity" values="0.65;1;0.65" dur="3.2s" begin="1.8s" repeatCount="indefinite"/>
      </rect>
    </g>
    """


def micro_ai(accent, mode):
    op = "0.42" if mode == "dark" else "0.28"
    return f"""
    <g transform="translate(338, 132)">
      <path d="M6 34 L28 6 L50 34 Z" fill="none" stroke="{accent}" stroke-opacity="{op}" stroke-width="1.2"/>
      <circle cx="6" cy="34" r="3.2" fill="{accent}" fill-opacity="0.55"/>
      <circle cx="28" cy="6" r="3.8" fill="{accent}" fill-opacity="0.88"/>
      <circle cx="50" cy="34" r="3.2" fill="{accent}" fill-opacity="0.55"/>
      <circle r="2.2" fill="{accent}">
        <animateMotion dur="3.8s" repeatCount="indefinite" path="M 6 34 L 28 6 L 50 34 L 6 34"/>
      </circle>
    </g>
    """


def micro_nav(accent, mode):
    op = "0.35" if mode == "dark" else "0.24"
    return f"""
    <g transform="translate(320, 128)">
      <rect x="0" y="4" width="72" height="40" rx="6" fill="none" stroke="{accent}" stroke-opacity="{op}" stroke-width="1"/>
      <path d="M10 34 L26 34 L26 16 L50 16 L50 26 L62 26" fill="none" stroke="{accent}" stroke-opacity="0.65" stroke-width="1.5" stroke-dasharray="3 2.5"/>
      <circle cx="10" cy="34" r="2.6" fill="{accent}" fill-opacity="0.5"/>
      <circle cx="62" cy="26" r="3.0" fill="{accent}"/>
      <circle r="2.4" fill="{accent}">
        <animateMotion dur="4.2s" repeatCount="indefinite" path="M 10 34 L 26 34 L 26 16 L 50 16 L 50 26 L 62 26"/>
      </circle>
    </g>
    """


def micro_custom(accent, mode):
    op = "0.38" if mode == "dark" else "0.25"
    return f"""
    <g transform="translate(328, 138)">
      <rect x="0" y="10" width="14" height="14" rx="3.5" fill="{accent}" fill-opacity="0.16" stroke="{accent}" stroke-opacity="{op}" stroke-width="1.1"/>
      <rect x="24" y="10" width="14" height="14" rx="3.5" fill="{accent}" fill-opacity="0.22" stroke="{accent}" stroke-opacity="0.6" stroke-width="1.1"/>
      <rect x="48" y="10" width="14" height="14" rx="3.5" fill="{accent}" fill-opacity="0.16" stroke="{accent}" stroke-opacity="{op}" stroke-width="1.1"/>
      <line x1="14" y1="17" x2="24" y2="17" stroke="{accent}" stroke-opacity="{op}" stroke-width="1.2"/>
      <line x1="38" y1="17" x2="48" y2="17" stroke="{accent}" stroke-opacity="{op}" stroke-width="1.2"/>
      <circle r="2.1" fill="{accent}">
        <animateMotion dur="3.4s" repeatCount="indefinite" path="M 14 17 L 48 17"/>
      </circle>
    </g>
    """


# ---------------------------------------------------------------------------
# 5. ARCHITECTURE STACK + ENGINEERING PRINCIPLES (840 x 288)
# ---------------------------------------------------------------------------
def build_stack(mode="dark"):
    W, H = 840, 288
    if mode == "dark":
        bg1, bg2 = "#131227", "#181632"
        border = "#2E2B50"
        sheen_op = "0.10"
        header_fg = "#A296FA"
        label_fg = "#F4F2FC"
        muted = "#9B96B8"
        row_line = "#252242"
        # Primary vs secondary pill hierarchy
        pri_bg = "#221F44"
        pri_border = "#484284"
        pri_fg = "#F4F2FC"
        sec_bg = "#191730"
        sec_border = "#2D2A4E"
        sec_fg = "#B7B3CE"
        tenet_num = "#A296FA"
    else:
        bg1, bg2 = "#FCFBF8", "#F4F1EA"
        border = "#DDD8CE"
        sheen_op = "0.85"
        header_fg = "#4338CA"
        label_fg = "#17162B"
        muted = "#5D5A73"
        row_line = "#E6E1D8"
        pri_bg = "#FFFFFF"
        pri_border = "#B8B2EE"
        pri_fg = "#1E1B4B"
        sec_bg = "#F4F1EA"
        sec_border = "#DDD8CE"
        sec_fg = "#4D4A61"
        tenet_num = "#4338CA"

    # (Category, dot color, [(label, is_primary), ...])
    rows = [
        ("Mobile & Web", "#60A5FA" if mode == "dark" else "#2563EB",
         [("Flutter", True), ("Dart", True), ("TypeScript", True), ("React", False), ("Next.js", False), ("Swift", False), ("Kotlin", False)]),
        ("Backend & Data", "#4FBF92" if mode == "dark" else "#166549",
         [("PostgreSQL", True), ("PL/pgSQL", True), ("Supabase", True), ("Node.js", False), ("Python", False), ("Go", False), ("Redis", False)]),
        ("AI & Agents", "#A296FA" if mode == "dark" else "#4338CA",
         [("AI Agents", True), ("Arabic & Voice AI", True), ("OpenAI", False), ("Claude", False), ("Gemini", False), ("Llama", False)]),
        ("Cloud & Infra", "#F2A65A" if mode == "dark" else "#C2590C",
         [("AWS", True), ("Google Cloud", True), ("Docker", False), ("Azure", False), ("Firebase", False), ("GitHub Actions", False)]),
    ]

    row_svgs = []
    y0 = 54
    row_h = 39
    for idx, (cat, dot, items) in enumerate(rows):
        y = y0 + idx * row_h
        if idx > 0:
            row_svgs.append(f'<line x1="24" y1="{y - 11}" x2="{W - 24}" y2="{y - 11}" stroke="{row_line}" stroke-width="1"/>')
        row_svgs.append(f'<circle cx="32" cy="{y + 8}" r="4" fill="{dot}"/>')
        row_svgs.append(f'<text x="46" y="{y + 12.2}" font-family="{FONT_SANS}" font-size="12.8" font-weight="600" fill="{label_fg}">{escape(cat)}</text>')

        cx = 178
        for label, is_pri in items:
            w = pill_width(label, min_w=54, char_w=7.4, pad=26 if is_pri else 22)
            p_bg = pri_bg if is_pri else sec_bg
            p_bd = pri_border if is_pri else sec_border
            p_fg = pri_fg if is_pri else sec_fg
            fw = "600" if is_pri else "500"
            dot_mark = f'<circle cx="{cx + 10}" cy="{y + 8}" r="2.3" fill="{dot}"/>' if is_pri else ""
            tx = cx + w / 2.0 + (4 if is_pri else 0)
            row_svgs.append(f"""
            <rect x="{cx}" y="{y - 5}" width="{w}" height="26" rx="7" fill="{p_bg}" stroke="{p_bd}" stroke-width="1"/>
            {dot_mark}
            <text x="{tx:.1f}" y="{y + 12}" text-anchor="middle" font-family="{FONT_SANS}" font-size="11.5" font-weight="{fw}" fill="{p_fg}">{escape(label)}</text>
            """)
            cx += w + 8

    # Integrated 3-Column Engineering Tenets Strip at bottom
    tenets = [
        ("01 · UNIFIED DATA CORE", "Single real-time relational ledger,", "zero fragmented enterprise silos."),
        ("02 · GOVERNED AI", "Role-scoped agents with full audit", "trails and human team approval."),
        ("03 · FIELD-READY CRAFT", "Cross-platform UX engineered for", "high-volume daily operations."),
    ]
    tenet_svgs = [f'<line x1="24" y1="210" x2="{W - 24}" y2="210" stroke="{row_line}" stroke-width="1"/>']
    col_w = (W - 48) / 3.0
    for idx, (head, l1, l2) in enumerate(tenets):
        tx = 26 + idx * col_w
        if idx > 0:
            tenet_svgs.append(f'<line x1="{tx - 10:.1f}" y1="222" x2="{tx - 10:.1f}" y2="274" stroke="{row_line}" stroke-width="1"/>')
        tenet_svgs.append(f"""
        <text x="{tx:.1f}" y="233" font-family="{FONT_MONO}" font-size="10.2" font-weight="700" letter-spacing="0.8" fill="{tenet_num}">{escape(head)}</text>
        <text x="{tx:.1f}" y="252" font-family="{FONT_SANS}" font-size="11.8" fill="{muted}">{escape(l1)}</text>
        <text x="{tx:.1f}" y="268" font-family="{FONT_SANS}" font-size="11.8" fill="{muted}">{escape(l2)}</text>
        """)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Core Architecture, Technology Stack, and Engineering Principles">
  <defs>
    <linearGradient id="st_bg_{mode}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{bg1}"/>
      <stop offset="100%" stop-color="{bg2}"/>
    </linearGradient>
    <clipPath id="st_clip_{mode}">
      <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="14"/>
    </clipPath>
  </defs>
  <g clip-path="url(#st_clip_{mode})">
    <rect width="{W}" height="{H}" fill="url(#st_bg_{mode})"/>
    <line x1="20" y1="1.5" x2="{W-20}" y2="1.5" stroke="#FFFFFF" stroke-opacity="{sheen_op}" stroke-width="1"/>
    <text x="26" y="30" font-family="{FONT_MONO}" font-size="11" font-weight="700" letter-spacing="1.1" fill="{header_fg}">CORE ARCHITECTURE &amp; TECHNOLOGY STACK</text>
    <text x="{W - 26}" y="30" text-anchor="end" font-family="{FONT_MONO}" font-size="9.5" font-weight="600" letter-spacing="0.6" fill="{muted}">PRIMARY CORE HIGHLIGHTED</text>
    {''.join(row_svgs)}
    {''.join(tenet_svgs)}
  </g>
  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="14" fill="none" stroke="{border}" stroke-width="1"/>
</svg>
"""
    save_svg(ASSETS_DIR / f"stack-{mode}.svg", svg)


def build_avatar():
    S = 800
    logo_defs, logo_paths = qodra_logo_group(400, 400, 1.45, mode="dark", uid="av")
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{S}" height="{S}" viewBox="0 0 {S} {S}">
  <defs>
    <linearGradient id="av_bg" x1="15%" y1="0%" x2="85%" y2="100%">
      <stop offset="0%" stop-color="#2A2752"/>
      <stop offset="55%" stop-color="#18172A"/>
      <stop offset="100%" stop-color="#0D0C18"/>
    </linearGradient>
    <radialGradient id="av_glow" cx="50%" cy="46%" r="52%">
      <stop offset="0%" stop-color="#5A52EA" stop-opacity="0.34"/>
      <stop offset="100%" stop-color="#5A52EA" stop-opacity="0"/>
    </radialGradient>
    {logo_defs}
  </defs>
  <rect width="{S}" height="{S}" fill="url(#av_bg)"/>
  <rect width="{S}" height="{S}" fill="url(#av_glow)"/>
  <polygon points="{hex_points(400, 400, 330, True)}" fill="none" stroke="#9A8DF8" stroke-opacity="0.22" stroke-width="3"/>
  {logo_paths}
</svg>
"""
    save_svg(ASSETS_DIR / "avatar-qodra.svg", svg)


# Exact Lucide & Simple Icons 24x24 vector geometry
ICON_ID_CARD = (
    '<rect x="2" y="4.5" width="20" height="15" rx="2.5"/>'
    '<circle cx="8.5" cy="10.2" r="2"/>'
    '<path d="M5.4 15.8c.6-1.5 1.8-2.2 3.1-2.2s2.5.7 3.1 2.2"/>'
    '<path d="M14.5 9.8h4.5M14.5 13.4h3.5"/>'
)
ICON_GLOBE = (
    '<circle cx="12" cy="12" r="9.5"/>'
    '<path d="M2.5 12h19"/>'
    '<path d="M12 2.5a14.5 14.5 0 0 1 0 19 14.5 14.5 0 0 1 0-19Z"/>'
)
ICON_EMAIL = (
    '<rect x="2.5" y="4.5" width="19" height="15" rx="2.5"/>'
    '<path d="M3.2 6.2l7.6 5.4a2 2 0 0 0 2.4 0l7.6-5.4"/>'
)
ICON_WHATSAPP = (
    '<path d="M12.04 2c-5.46 0-9.91 4.45-9.91 9.91 0 1.75.46 3.45 1.32 4.95L2.05 22l5.25-1.38'
    'a9.87 9.87 0 0 0 4.74 1.21h.01c5.46 0 9.9-4.45 9.9-9.91 0-2.65-1.03-5.14-2.9-7.01A9.82 9.82 0 0 0 12.04 2Z'
    'm0 16.27a8.12 8.12 0 0 1-4.14-1.14l-.3-.18-3.1.81.83-3.02-.19-.31a8.16 8.16 0 1 1 6.9 3.84Z'
    'm4.47-6.08c-.25-.13-1.48-.73-1.71-.82-.23-.09-.39-.13-.56.12-.17.25-.65.82-.8 1-.15.17-.3.19-.55.06'
    '-.25-.13-1.05-.39-2-1.23-.74-.66-1.24-1.48-1.38-1.73-.14-.25-.02-.38.11-.5.11-.11.25-.3.38-.45'
    '.13-.15.17-.25.26-.42.09-.17.04-.32-.02-.45-.06-.13-.56-1.35-.77-1.85-.2-.48-.4-.42-.56-.43h-.48'
    'c-.17 0-.45.06-.68.31-.23.25-.89.87-.89 2.12 0 1.25.91 2.46 1.04 2.63.13.17 1.8 2.75 4.36 3.85'
    '.61.26 1.09.42 1.46.54.61.2 1.17.17 1.61.1.49-.07 1.48-.6 1.69-1.18.21-.58.21-1.08.15-1.18'
    '-.06-.1-.23-.16-.48-.29Z"/>'
)


def main():
    metrics = fetch_live_metrics()
    for mode in ("dark", "light"):
        build_hero(mode)
        build_telemetry(metrics, mode)
        build_stack(mode)

        build_action_button("btn-card", "Digital Card", ICON_ID_CARD, icon_mode="stroke", variant="primary", width=168, mode=mode)
        build_action_button("btn-web", "qodrasystems.com", ICON_GLOBE, icon_mode="stroke", variant="secondary", width=196, mode=mode)
        build_action_button("btn-email", "Email Me", ICON_EMAIL, icon_mode="stroke", variant="secondary", width=148, mode=mode)
        build_action_button("btn-whatsapp", "WhatsApp", ICON_WHATSAPP, icon_mode="fill", variant="whatsapp", width=156, mode=mode)

        build_product_card(
            "card-erp",
            "Qodra OS",
            "UNIFIED ERP · E-INVOICING",
            "Accounting, POS, inventory, purchasing, HR & sector modules",
            "on a single real-time database with e-invoicing built in.",
            ["ERP", "Finance & POS", "Multi-Branch"],
            "#4FBF92", "#166549",
            '<path d="M9 1L2 5v8l7 4 7-4V5L9 1z"/><path d="M2 5l7 4 7-4M9 9v8"/>',
            micro_erp,
            mode=mode,
        )
        build_product_card(
            "card-ai",
            "Awni & AI Agents",
            "PERMISSION-AWARE AI",
            "Arabic & voice AI agents that work inside company systems",
            "within role permissions, audit trails, and team approval.",
            ["AI Agents", "Arabic & Voice", "Enterprise"],
            "#A296FA", "#4338CA",
            '<path d="M9 1.5l1.8 4.7 4.7 1.8-4.7 1.8L9 14.5l-1.8-4.7L2.5 8l4.7-1.8L9 1.5z"/>',
            micro_ai,
            mode=mode,
        )
        build_product_card(
            "card-nav",
            "Indoor Navigation",
            "GPS-FREE WAYFINDING",
            "Cross-floor visitor guidance app and live admin console",
            "built for malls, airports, hospitals, campuses & museums.",
            ["Cross-Floor", "Heatmaps", "Venues"],
            "#C084FC", "#6D28D9",
            '<path d="M9 16s5.5-4.8 5.5-9A5.5 5.5 0 1 0 3.5 7c0 4.2 5.5 9 5.5 9z"/><circle cx="9" cy="7" r="2"/>',
            micro_nav,
            mode=mode,
        )
        build_product_card(
            "card-custom",
            "Custom Systems & Apps",
            "BESPOKE PLATFORMS",
            "Tailored operational software, Flutter & web platforms,",
            "customer/supplier portals, and scalable cloud integrations.",
            ["Mobile & Web", "APIs & Cloud", "Custom"],
            "#60A5FA", "#1D4ED8",
            '<path d="M5.5 5L1.5 9l4 4M12.5 5l4 4-4 4M10.5 3l-3 12"/>',
            micro_custom,
            mode=mode,
        )

    build_avatar()
    print("v2 executive dashboard assets generated & XML-validated in", ASSETS_DIR)


if __name__ == "__main__":
    main()
