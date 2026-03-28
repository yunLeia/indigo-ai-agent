from __future__ import annotations

from typing import Any

from app.contracts import ScenarioName


def build_raw_context(scenario: ScenarioName) -> dict[str, Any]:
    if scenario == "hospital":
        return {
            "scenarioHint": "hospital_pa",
            "city": "New York City",
            "neighborhood": "Midtown East",
            "venueType": "hospital",
            "userSituationHint": "waiting_room",
            "timeHint": "morning",
            "weatherHint": "clear",
            "notes": ["Hospital lobby", "Realtime assistive announcement flow"],
        }

    return {
        "scenarioHint": "emergency_vehicle",
        "city": "New York City",
        "neighborhood": "Chelsea",
        "venueType": "street",
        "userSituationHint": "on_foot",
        "timeHint": "afternoon",
        "weatherHint": "clear",
        "notes": ["Outdoor demo route", "Realtime hazard awareness flow"],
    }
