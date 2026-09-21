from __future__ import annotations
from math import isfinite

RANGES = {
    'soil_moisture': (0, 100),
    'temperature': (-20, 70),
    'humidity': (0, 100),
}

# How big a jump between consecutive readings counts as "noisy" / a sudden jump.
JUMP_THRESHOLD = {
    'soil_moisture': 20,
    'temperature': 12,
    'humidity': 20,
}

REPEAT_STREAK_MIN = 4  # this many identical consecutive readings is suspicious (a "stuck" sensor)


def _label_for(name: str) -> str:
    return name.replace('_', ' ')


def assess_sensors(values: dict, previous: dict | None = None, recent_history: list[dict] | None = None) -> dict:
    """Validate a sensor reading and flag anomalies.

    Backward compatible with v3.2 callers: the ``overall`` and ``sensors``
    keys keep their original meaning and shape. v3.3 adds ``anomalies``
    (a list of plain-language findings) and ``anomaly_detected`` (bool), and
    optionally uses ``recent_history`` (most-recent-first list of past raw
    reading dicts for the same device) to detect a sensor stuck on one value.
    """
    statuses = {}
    score = 1.0
    anomalies: list[str] = []

    for name, (lo, hi) in RANGES.items():
        v = values.get(name)
        if v is None:
            statuses[name] = {'status': 'disconnected', 'valid': False}
            score *= 0.7
            anomalies.append(f"{_label_for(name).capitalize()} reading is missing (sensor disconnected?).")
            continue
        try:
            v = float(v)
        except (TypeError, ValueError):
            statuses[name] = {'status': 'invalid', 'valid': False}
            score *= 0.35
            anomalies.append(f"{_label_for(name).capitalize()} value is not numeric.")
            continue
        if not isfinite(v) or v < lo or v > hi:
            statuses[name] = {'status': 'invalid', 'valid': False}
            score *= 0.35
            anomalies.append(
                f"{_label_for(name).capitalize()} reading of {v} is outside the physically plausible "
                f"range ({lo} to {hi}); the sensor may be faulty."
            )
            continue

        noisy = False
        if previous and previous.get(name) is not None:
            try:
                prev_v = float(previous[name])
                if abs(v - prev_v) > JUMP_THRESHOLD[name]:
                    noisy = True
                    anomalies.append(
                        f"{_label_for(name).capitalize()} jumped from {prev_v} to {v} between consecutive "
                        f"readings — a sudden change worth double-checking."
                    )
            except (TypeError, ValueError):
                pass

        stuck = False
        if recent_history:
            series = [values.get(name)] + [h.get(name) for h in recent_history]
            series = [s for s in series if s is not None]
            if len(series) >= REPEAT_STREAK_MIN and len(set(round(float(s), 3) for s in series[:REPEAT_STREAK_MIN])) == 1:
                stuck = True
                anomalies.append(
                    f"{_label_for(name).capitalize()} has reported the exact same value "
                    f"{REPEAT_STREAK_MIN} times in a row — the sensor may be stuck rather than truly stable."
                )

        status = 'stuck' if stuck else ('noisy' if noisy else 'healthy')
        statuses[name] = {'status': status, 'valid': True}
        if stuck:
            score *= 0.6
        elif noisy:
            score *= 0.8

    if previous and values.get('recorded_at') and previous.get('recorded_at') and values['recorded_at'] < previous.get('recorded_at', 0):
        score *= 0.5
        anomalies.append("Reading timestamp is older than the previous stored reading (out-of-order data).")

    overall = round(max(0.0, min(1.0, score)), 3)
    return {
        'overall': overall,
        'sensors': statuses,
        'anomalies': anomalies,
        'anomaly_detected': len(anomalies) > 0,
    }
