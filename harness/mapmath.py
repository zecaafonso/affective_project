"""Pure geometry for the affective map (no GUI needed, so it can be tested)."""

SIZE = 460
MARGIN = 44


def project_point(valence, activity, dominance, three_d, size=SIZE, margin=MARGIN):
    """Map (valence, activity[, dominance]) in [-1, 1] to canvas pixels."""
    cx = cy = size / 2.0
    r = (size - 2 * margin) / 2.0
    if three_d and dominance is not None:
        return cx + r * (0.8 * valence + 0.25 * dominance), cy - r * (0.8 * activity + 0.2 * dominance)
    return cx + r * valence, cy - r * activity
