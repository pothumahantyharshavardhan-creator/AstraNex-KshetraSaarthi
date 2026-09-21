"""Structured alert engine (v3.3, spec section 13).

Produces alert objects with a bounded severity vocabulary (INFO / WATCH /
WARNING / CRITICAL) and four required narrative fields: what happened, why
it matters, what to check, and a suggested next action. This sits alongside
(does not replace) the existing simple HIGH/MODERATE alert rows already
persisted by v3.2's ``db.add_alert`` — the richer structure is returned to
the caller so the frontend can render it, without a breaking schema change.

This module never manufactures alarm: severity is only raised when a
concrete trigger condition (defined below) is met, and language avoids
absolute claims ("may indicate", "recommended") per the project's
no-false-claims rule.
"""
from __future__ import annotations

LEVELS = ("INFO", "WATCH", "WARNING", "CRITICAL")
_RANK = {lvl: i for i, lvl in enumerate(LEVELS)}


def _escalate(current: str, candidate: str) -> str:
    return candidate if _RANK[candidate] > _RANK[current] else current


def build_alerts(analysis: dict, data_quality: dict | None = None, sensor_anomalies: list[str] | None = None) -> list[dict]:
    """Build zero or more structured alerts from an engine analysis result.

    ``analysis`` is the dict returned by ``backend.engine.analyze_field``.
    Each returned alert has: level, title, what, why, check, action.
    """
    alerts: list[dict] = []
    risks = analysis.get('risks', {})
    evidence = analysis.get('evidence', {})
    m = evidence.get('soil_moisture')
    t = evidence.get('temperature')

    # --- Water stress ---
    water_risk = risks.get('water', 0)
    if water_risk >= 65:
        alerts.append({
            'level': 'WARNING',
            'title': 'Low soil moisture',
            'what': f"Soil moisture is reading {m}%, and the water-stress risk signal is {water_risk:.0f}%.",
            'why': "Sustained low moisture during active growth stages can slow growth and increase crop stress.",
            'check': "Check soil moisture at the root zone directly, not just at the sensor location.",
            'action': analysis.get('irrigation', {}).get('reason', 'Consider irrigation and recheck soil moisture after watering.'),
        })
    elif water_risk >= 40:
        alerts.append({
            'level': 'WATCH',
            'title': 'Soil moisture trending low',
            'what': f"Soil moisture is {m}%, moderately below the comfortable range for this field context.",
            'why': "This is not yet critical but is worth monitoring, especially if no rain is expected.",
            'check': "Recheck soil moisture in a few hours or after the next scheduled reading.",
            'action': "No irrigation forced yet; continue monitoring.",
        })

    # --- Excess water / flood risk ---
    excess_risk = risks.get('excess_water', 0)
    if excess_risk >= 65:
        alerts.append({
            'level': 'WARNING',
            'title': 'Excess water / flood risk',
            'what': f"Excess-water risk signal is {excess_risk:.0f}%, based on rainfall, weather and moisture readings.",
            'why': "Waterlogged roots can cause oxygen stress and increase disease pressure.",
            'check': "Check for standing water and drainage around the root zone.",
            'action': "Hold irrigation until conditions clear; verify drainage.",
        })

    # --- Heat stress ---
    heat_risk = risks.get('heat', 0)
    if heat_risk >= 65:
        alerts.append({
            'level': 'WARNING',
            'title': 'Heat stress risk',
            'what': f"Temperature is reading {t}°C and the heat-stress risk signal is {heat_risk:.0f}%.",
            'why': "Prolonged heat stress can affect flowering, fruit set and overall vigor for many crops.",
            'check': "Check leaf wilting and canopy exposure during the hottest part of the day.",
            'action': "Consider shading or adjusted irrigation timing where locally appropriate; monitor closely.",
        })

    # --- Disease / pest signal ---
    disease_risk = risks.get('disease', 0)
    issue = analysis.get('issue', '')
    if issue.startswith('disease') and disease_risk >= 55:
        level = 'CRITICAL' if analysis.get('color') == 'red' else 'WARNING'
        alerts.append({
            'level': level,
            'title': 'Disease-risk signal detected',
            'what': f"A visual/contextual pattern consistent with {analysis.get('disease') or 'a disease signal'} was detected (disease-risk signal {disease_risk:.0f}%).",
            'why': "Undetected disease can spread within a field if not verified and addressed early.",
            'check': "Inspect several plants in the affected area, not just the one scanned.",
            'action': "Treat this as preliminary screening only; confirm locally before any crop-protection treatment.",
        })
    elif issue == 'pest':
        alerts.append({
            'level': 'WATCH',
            'title': 'Possible pest activity',
            'what': "Visual evidence consistent with pest damage (chewed edges / holes) was noted.",
            'why': "Early pest activity can escalate if left unchecked.",
            'check': "Inspect the underside of several leaves for insects or eggs.",
            'action': "Continue scouting; escalate if damage spreads.",
        })

    # --- Sensor anomalies ---
    if sensor_anomalies:
        alerts.append({
            'level': 'WARNING' if len(sensor_anomalies) > 1 else 'WATCH',
            'title': 'Sensor anomaly detected',
            'what': sensor_anomalies[0] if len(sensor_anomalies) == 1 else f"{len(sensor_anomalies)} sensor anomalies were detected on this reading.",
            'why': "Analyses built on faulty sensor data can be misleading even if the logic is otherwise sound.",
            'check': "Physically inspect the flagged sensor(s) for damage, poor placement, or a drained battery.",
            'action': "Treat this reading's conclusions with reduced confidence until the sensor is verified.",
        })

    # --- Data quality ---
    if data_quality and data_quality.get('band') == 'POOR':
        alerts.append({
            'level': 'WATCH',
            'title': 'Low data quality for this analysis',
            'what': data_quality.get('explanation', 'Input data quality is low for this analysis.'),
            'why': "Low-quality inputs reduce how much weight this specific analysis should be given.",
            'check': "Review the data-quality breakdown for the specific missing or inconsistent field.",
            'action': "Re-run the analysis once fresher, more complete sensor data is available.",
        })

    if not alerts:
        alerts.append({
            'level': 'INFO',
            'title': 'No active alerts',
            'what': "No configured alert trigger was met for this reading.",
            'why': "This does not certify field health; it only means no monitored threshold was crossed.",
            'check': "Continue routine scouting.",
            'action': "No action required at this time.",
        })

    return alerts


def overall_level(alerts: list[dict]) -> str:
    level = 'INFO'
    for a in alerts:
        level = _escalate(level, a.get('level', 'INFO'))
    return level
