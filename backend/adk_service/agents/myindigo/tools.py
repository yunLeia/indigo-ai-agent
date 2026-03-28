from __future__ import annotations

from typing import Any


def assess_vehicle_sound(
    sound_type: str,
    direction: str,
    user_state: str,
    location: str,
) -> dict[str, Any]:
    return {
        "sound": sound_type,
        "risk": "HIGH" if sound_type == "siren" else "MEDIUM",
        "title": "Emergency vehicle approaching"
        if sound_type == "siren"
        else "Vehicle sound nearby",
        "subtitle": "Move right and yield"
        if sound_type == "siren"
        else "Check surroundings",
        "direction": direction,
        "user_state": user_state,
        "location": location,
    }


def extract_name_announcement(
    transcript: str,
    user_name: str,
    location_type: str,
) -> dict[str, Any]:
    lowered = transcript.lower()
    found = user_name.lower() in lowered

    return {
        "name_found": found,
        "title": "Your name was called" if found else "Announcement detected",
        "subtitle": "Go to Exam Room 3"
        if "exam room 3" in lowered
        else "Check the latest details",
        "location_detail": "Exam Room 3" if "exam room 3" in lowered else None,
        "location_type": location_type,
    }


def build_alert_payload(
    title: str,
    subtitle: str,
    risk: str,
    scenario: str,
) -> dict[str, Any]:
    return {
        "scenario": scenario,
        "title": title,
        "subtitle": subtitle,
        "risk": risk,
    }
