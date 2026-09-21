"""Time-series field history and farm-events timeline (v3.3, spec sections 11-12).

Both functions only ever summarise data that is actually in the database.
Neither fabricates historical values: when there isn't enough history for a
requested window, the response says so explicitly instead of interpolating
or inventing points.
"""
from __future__ import annotations
import time

WINDOWS_SECONDS = {'24h': 24 * 3600, '7d': 7 * 24 * 3600, '30d': 30 * 24 * 3600}
MIN_POINTS_FOR_WINDOW = 2


def field_history(sensor_rows: list[dict], observation_rows: list[dict], window: str = '24h', now: float | None = None) -> dict:
    """Bucket recent sensor + observation data into a requested time window.

    ``sensor_rows`` / ``observation_rows`` are the raw dict rows as returned
    by ``backend.db.latest_sensors`` / ``backend.db.recent_observations``
    (already-fetched — this function does no I/O so it stays trivially
    testable).
    """
    if window not in WINDOWS_SECONDS:
        window = '24h'
    now = now if now is not None else time.time()
    cutoff = now - WINDOWS_SECONDS[window]

    moisture, temperature, humidity, health = [], [], [], []
    for r in sensor_rows:
        ts = r.get('recorded_at') or r.get('received_at')
        if ts is None or ts < cutoff:
            continue
        if r.get('soil_moisture') is not None:
            moisture.append({'t': ts, 'v': r['soil_moisture']})
        if r.get('temperature') is not None:
            temperature.append({'t': ts, 'v': r['temperature']})
        if r.get('humidity') is not None:
            humidity.append({'t': ts, 'v': r['humidity']})

    for o in observation_rows:
        ts = o.get('created_at')
        if ts is None or ts < cutoff:
            continue
        score = (o.get('result') or {}).get('health_score')
        if score is not None:
            health.append({'t': ts, 'v': score})

    series = {'soil_moisture': moisture, 'temperature': temperature, 'humidity': humidity, 'health_score': health}
    for k in series:
        series[k].sort(key=lambda p: p['t'])

    insufficient = [k for k, v in series.items() if len(v) < MIN_POINTS_FOR_WINDOW]
    return {
        'window': window,
        'series': series,
        'insufficient_data_for': insufficient,
        'message': None if not insufficient else
            f"Not enough historical data for: {', '.join(insufficient)} in the last {window}.",
    }


def farm_events_timeline(observations: list[dict], sensor_rows: list[dict], alerts: list[dict],
                          irrigation_events: list[dict], limit: int = 40) -> list[dict]:
    """Merge observations, sensor readings, alerts and irrigation events into
    one chronological, farmer-readable timeline. Never invents an event."""
    events = []
    for o in observations:
        ts = o.get('created_at')
        if ts is None:
            continue
        result = o.get('result') or {}
        events.append({'ts': ts, 'kind': 'analysis', 'label': f"Plant/field analysis: {result.get('health_status', 'result')}"})
        if result.get('issue') and result.get('issue') not in {'healthy'}:
            events.append({'ts': ts + 0.001, 'kind': 'signal', 'label': f"Signal noted: {result.get('issue')}"})

    for s in sensor_rows:
        ts = s.get('recorded_at') or s.get('received_at')
        if ts is None:
            continue
        events.append({'ts': ts, 'kind': 'sensor', 'label': 'Sensor reading received'})
        health = s.get('health') or {}
        if health.get('anomaly_detected'):
            events.append({'ts': ts + 0.001, 'kind': 'sensor_anomaly', 'label': 'Sensor anomaly detected'})

    for a in alerts:
        ts = a.get('created_at')
        if ts is None:
            continue
        events.append({'ts': ts, 'kind': 'alert', 'label': f"Alert ({a.get('severity', a.get('level', 'INFO'))}): {a.get('kind', '')}"})

    for e in irrigation_events:
        ts = e.get('requested_at')
        if ts is None:
            continue
        events.append({'ts': ts, 'kind': 'irrigation', 'label': f"Irrigation {e.get('status', 'event')} ({e.get('duration_min', 0)} min)"})

    events.sort(key=lambda e: e['ts'])
    return events[-limit:]
