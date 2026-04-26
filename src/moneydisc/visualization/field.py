"""Ultimate frisbee field drawing utilities."""

from __future__ import annotations

import matplotlib.axes
import matplotlib.pyplot as plt

from moneydisc.analysis.config import ENDZONE_DEPTH_M, FIELD_LENGTH_M, FIELD_WIDTH_M


def draw_field() -> matplotlib.axes.Axes:
    """Draw a standard ultimate frisbee field and return the axes.

    The Y-axis is inverted so dist_to_endzone=0 (attacking end) is at the top,
    matching the Statto coordinate convention where Y=0 is the back of the
    opponent's endzone.
    """
    plt.figure(figsize=(20, 8))
    ax = plt.gca()

    field_width = FIELD_WIDTH_M
    total_field_length = FIELD_LENGTH_M
    central_zone_length = FIELD_LENGTH_M - 2 * ENDZONE_DEPTH_M

    ax.plot([0, field_width], [0, 0], color="black")
    ax.plot([0, field_width], [-18, -18], color="black")
    ax.plot([0, field_width], [central_zone_length, central_zone_length], color="black")
    ax.plot([0, field_width], [total_field_length - 18, total_field_length - 18], color="black")
    ax.plot([0, 0], [-18, total_field_length - 18], color="black")
    ax.plot([field_width, field_width], [-18, total_field_length - 18], color="black")

    ax.plot(
        [field_width / 2, field_width / 2], [18, 18],
        color="black", linestyle="--", marker="o", markersize=5,
    )
    ax.plot(
        [field_width / 2, field_width / 2], [central_zone_length - 18, central_zone_length - 18],
        color="black", linestyle="--", marker="o", markersize=5,
    )

    ax.plot(
        [0, field_width], [central_zone_length / 2, central_zone_length / 2],
        color="black", linestyle="--",
    )

    ax.set_xlim(-5, field_width + 5)
    ax.set_ylim(-20, total_field_length - 18 + 5)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Field Width (m)")
    ax.set_ylabel("Distance from Far Endzone (m)")
    ax.invert_yaxis()

    return ax
