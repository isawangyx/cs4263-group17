#!/usr/bin/env python3
"""Shared helpers and schemas for the Group 17 experiment."""

from __future__ import annotations

import json
from pathlib import Path


def hhmm(value: str) -> int:
    hours, minutes = map(int, value.split(":"))
    return hours * 60 + minutes


def load_benchmark(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def jsonl_read(path: str | Path) -> list[dict]:
    source = Path(path)
    if not source.exists():
        return []
    return [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]


def jsonl_write(path: str | Path, rows: list[dict]) -> None:
    Path(path).write_text(
        "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


ITINERARY_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["FEASIBLE", "INFEASIBLE"]},
        "outbound_flight_id": {"type": "string"},
        "return_flight_id": {"type": "string"},
        "hotel_id": {"type": "string"},
        "schedule": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "slot_id": {"type": "string"},
                    "attraction_id": {"type": "string"},
                },
                "required": ["slot_id", "attraction_id"],
                "additionalProperties": False,
            },
        },
        "declared_total_cost": {"type": "integer"},
        "verification_notes": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "status",
        "outbound_flight_id",
        "return_flight_id",
        "hotel_id",
        "schedule",
        "declared_total_cost",
        "verification_notes",
    ],
    "additionalProperties": False,
}
