"""Configuration constants for Wall City 2025 stats analysis."""

from __future__ import annotations

# Ultimate frisbee field dimensions (meters)
FIELD_LENGTH_M = 100
ENDZONE_DEPTH_M = 18
FIELD_WIDTH_M = 36
FIELD_CENTER_M = FIELD_WIDTH_M / 2  # 18 — used for dist_from_middle calculations

GAMES: dict[str, str] = {
    "Heidees 2025-05-18_20-38-33": "Heidees - Tom's Tourney",
    "Italy Masters 2025-05-25_11-05-03": "Italy Masters - Tom's Tourney",
    "Tchac 2025-05-25_17-52-13": "Tchac - Tom's Tourney",
    "FAB 2025-05-29_10-05-10": "FAB - Tom's Tourney",
    "IznoGood 2025-05-03_13-15-00": "Iznogood - Tom's Tourney",
    "Tchac Final 2025-06-01_14-30-00": "Tchac Final - Elite Invite",
    "Tchac 2025-05-30_17-24-00": "Tchac Pool - Elite Invite",
    "Grut 2025-05-31_17-45-00": "Grut - Elite Invite",
    "Chevron Action Flash   2025-05-31_12-30-00": "Chevy - Elite Invite",
    "FrankN 2025-07-04_10-40-00": "Frank N - DM 1",
    "Heidees Summer Inv 2025-05-02_10-52-50": "Heidees - Summer Invite",
    "Grut 2025-08-03_15-00-34": "Grut - Summer Invite",
    "Heidees 2025-09-07_14-00-22": "Heidees - Berlin Invite",
    "3SB 2025-09-07_12-00-12": "3SB - Berlin Invite",
}

NAME_MAPPINGS: dict[str, str] = {
    "09 Kryz Zajac": "09 Zajac",
    "02 Ondrej Rydlo": "02 Cego",
    "94 Jannis Wenderholm": "94 Jannis",
    "17 Steffen Linnemanstons": "17 Steffen",
    "03 Andres Brand": "03 Andres",
    "24 Philipp Steffan": "24 Philipp",
    "33 Ned Garvey": "33 Ned",
    "65 Ron Doempke": "65 Ron",
    "99 Bruno Jorginsons": "99 Bruno",
    "29 Ruben Ahlers": "29 Ruben",
    "21 Paul Herkens ": "21 Business",
    "13 Hartley Greenwald": "13 Hartley",
    "13 Hartley ": "13 Hartley",
    "13  Hartley": "13 Hartley",
    "47 Conrad Schlor": "47 Conrad",
    "20 Phil Kaye": "20 Phil",
    "77 David Metzger": "77 David",
    "10 Leo Eichler": "10 Leo",
    "18 Thorben Haag": "18 Thorben",
    "36 Yannick Marburg": "36 Yannick",
    "25 Vlad Basov": "25 Vlad",
    "34 Stefan Kuhn": "34 Icey",
    "14 Robin Chan": "44 Robin",
}

POSSESSION_MODEL_FILE = "linear_gp.p"
POINT_MODEL_FILE = "linear_point_scored.p"
