#!/usr/bin/env python3
"""Generate Group 17's deterministic travel-planning benchmark.

The generated prices, schedules, and venues are synthetic. They are intentionally
fixed so that the CSP and LLM receive identical, reproducible information.
"""

from __future__ import annotations

import argparse
import copy
import json
import random
from pathlib import Path


CITIES = [
    "Tokyo",
    "Seoul",
    "Bangkok",
    "Kuala Lumpur",
    "Taipei",
    "Hong Kong",
    "Osaka",
    "Hanoi",
    "Denpasar",
]
CATEGORIES = ["culture", "food", "nature", "shopping"]


def make_slots(duration: int) -> list[dict]:
    slots: list[dict] = []
    for day in range(1, duration + 1):
        if day == 1:
            periods = [("afternoon", "14:00", "16:00")]
        elif day == duration:
            periods = [("morning", "09:30", "11:30")]
        else:
            periods = [
                ("morning", "09:30", "11:30"),
                ("afternoon", "14:00", "16:00"),
            ]
        for period, start, end in periods:
            slots.append(
                {
                    "slot_id": f"D{day}_{period.upper()}",
                    "day": day,
                    "period": period,
                    "start": start,
                    "end": end,
                    "candidate_attraction_ids": [],
                }
            )
    return slots


def make_attractions(prefix: str, slots: list[dict], seed: int) -> list[dict]:
    attractions: list[dict] = []
    venue_words = ["Gallery", "Market", "Garden", "Arcade", "Museum", "Kitchen"]
    for slot_index, slot in enumerate(slots):
        for option_index in range(3):
            attraction_id = f"{prefix}_A{slot_index + 1}_{option_index + 1}"
            category = CATEGORIES[(slot_index + option_index) % len(CATEGORIES)]
            price = 12 + ((seed + slot_index * 5 + option_index * 7) % 19)
            slot["candidate_attraction_ids"].append(attraction_id)
            attractions.append(
                {
                    "id": attraction_id,
                    "name": f"Synthetic {venue_words[(slot_index + option_index) % len(venue_words)]} {slot_index + 1}.{option_index + 1}",
                    "category": category,
                    "price": price,
                    "duration_minutes": 90,
                    "open": "08:30",
                    "close": "18:00",
                    "location_id": f"{prefix}_L{slot_index + 1}_{option_index + 1}",
                    "eligible_slot_ids": [slot["slot_id"]],
                }
            )
    return attractions


def minimum_cost(instance: dict) -> int:
    nights = instance["trip"]["duration_days"] - 1
    cheapest_flights = min(f["price"] for f in instance["flights"]["outbound"]) + min(
        f["price"] for f in instance["flights"]["return"]
    )
    cheapest_hotel = min(h["nightly_price"] for h in instance["hotels"]) * nights
    attraction_by_id = {a["id"]: a for a in instance["attractions"]}
    cheapest_activities = sum(
        min(attraction_by_id[a_id]["price"] for a_id in slot["candidate_attraction_ids"])
        for slot in instance["daily_slots"]
    )
    return (
        cheapest_flights
        + cheapest_hotel
        + cheapest_activities
        + instance["transport"]["daily_pass_price"] * instance["trip"]["duration_days"]
    )


def witness_cost(
    instance: dict, hotel_id: str, selected_override: list[str] | None = None
) -> tuple[int, list[str]]:
    duration = instance["trip"]["duration_days"]
    hotel = next(h for h in instance["hotels"] if h["id"] == hotel_id)
    attraction_by_id = {a["id"]: a for a in instance["attractions"]}
    selected = selected_override or [
        slot["candidate_attraction_ids"][0] for slot in instance["daily_slots"]
    ]
    cost = (
        instance["flights"]["outbound"][0]["price"]
        + instance["flights"]["return"][0]["price"]
        + hotel["nightly_price"] * (duration - 1)
        + sum(attraction_by_id[a_id]["price"] for a_id in selected)
        + instance["transport"]["daily_pass_price"] * duration
    )
    return cost, selected


def make_base_case(index: int, duration: int, difficulty: str) -> dict:
    city = CITIES[index]
    prefix = f"B{index + 1}"
    slots = make_slots(duration)
    attractions = make_attractions(prefix, slots, seed=index + duration)
    base_fare = 135 + index * 4

    instance = {
        "dataset_version": "2.0.0",
        "instance_id": "",
        "pair_id": f"P{index + 1:02d}",
        "difficulty": difficulty,
        "expected_feasible": True,
        "trip": {
            "origin": "Singapore",
            "destination": city,
            "start_date": "2026-12-01",
            "duration_days": duration,
            "travellers": 1,
            "currency": "SGD",
            "budget": 0,
        },
        "preferences": {
            "preferred_categories": ["culture", "food"],
            "utility_weights": {"preferred_category": 2, "non_preferred_category": 1},
        },
        "flights": {
            "outbound": [
                {
                    "id": f"{prefix}_FO1",
                    "depart": "07:00",
                    "arrive": "10:00",
                    "price": base_fare,
                },
                {
                    "id": f"{prefix}_FO2",
                    "depart": "09:00",
                    "arrive": "12:20",
                    "price": base_fare + 35,
                },
            ],
            "return": [
                {
                    "id": f"{prefix}_FR1",
                    "depart": "18:30",
                    "arrive": "21:30",
                    "price": base_fare + 10,
                },
                {
                    "id": f"{prefix}_FR2",
                    "depart": "15:00",
                    "arrive": "18:00",
                    "price": base_fare - 5,
                },
            ],
        },
        "hotels": [
            {
                "id": f"{prefix}_H1",
                "name": "Synthetic Riverside Hotel",
                "nightly_price": 62 + index,
                "rating": 3,
                "location_id": f"{prefix}_HOTEL_1",
            },
            {
                "id": f"{prefix}_H2",
                "name": "Synthetic Central Hotel",
                "nightly_price": 84 + index,
                "rating": 4,
                "location_id": f"{prefix}_HOTEL_2",
            },
        ],
        "daily_slots": slots,
        "attractions": attractions,
        "transport": {
            "daily_pass_price": 12,
            "default_travel_minutes": 20,
            "overrides": [],
        },
        "constraints": {
            "choose_exactly_one_outbound_flight": True,
            "choose_exactly_one_return_flight": True,
            "choose_exactly_one_hotel": True,
            "choose_exactly_one_attraction_per_slot": True,
            "attractions_must_be_unique": True,
            "use_only_supplied_option_ids": True,
            "respect_opening_hours": True,
            "respect_slot_times": True,
            "arrival_buffer_minutes": 90,
            "departure_buffer_minutes": 120,
            "maximum_travel_minutes_per_leg": 60,
            "minimum_hotel_rating": 0,
            "minimum_category_counts": {},
            "required_attraction_ids": [],
        },
        "ground_truth": {
            "construction": "synthetic_fixed_data",
            "infeasibility_mutation": None,
            "reason": "A witness itinerary is supplied for automated verification.",
            "witness": {},
        },
    }

    if difficulty == "medium":
        instance["constraints"]["minimum_hotel_rating"] = 3
        instance["constraints"]["maximum_travel_minutes_per_leg"] = 45
        instance["constraints"]["minimum_category_counts"] = {"culture": 1, "food": 1}
        witness_hotel = f"{prefix}_H1"
    elif difficulty == "high":
        instance["constraints"]["minimum_hotel_rating"] = 4
        instance["constraints"]["maximum_travel_minutes_per_leg"] = 30
        instance["constraints"]["minimum_category_counts"] = {"culture": 2, "food": 2}
        witness_hotel = f"{prefix}_H2"
    else:
        witness_hotel = f"{prefix}_H1"

    selected_override = None
    if difficulty == "high":
        attraction_by_id = {a["id"]: a for a in attractions}
        selected_override = []
        for slot_index, slot in enumerate(slots):
            wanted_category = "culture" if slot_index % 2 == 0 else "food"
            selected_override.append(
                next(
                    a_id
                    for a_id in slot["candidate_attraction_ids"]
                    if attraction_by_id[a_id]["category"] == wanted_category
                )
            )

    cost, selected = witness_cost(instance, witness_hotel, selected_override)
    if difficulty == "high":
        instance["constraints"]["required_attraction_ids"] = [selected[0], selected[-1]]
    instance["trip"]["budget"] = cost + 60
    instance["ground_truth"]["witness"] = {
        "outbound_flight_id": f"{prefix}_FO1",
        "return_flight_id": f"{prefix}_FR1",
        "hotel_id": witness_hotel,
        "attraction_ids_by_slot": selected,
        "total_cost": cost,
    }
    return instance


def strengthen(instance: dict, replica: int) -> dict:
    """Keep a verified constructive witness while adding binding distractors."""
    level = instance["difficulty"]
    slots = instance["daily_slots"]
    amap = {a["id"]: a for a in instance["attractions"]}
    selected = instance["ground_truth"]["witness"]["attraction_ids_by_slot"]
    # Same constraint families at all levels; strength varies, not family presence.
    instance["constraints"]["minimum_hotel_rating"] = {"low": 3, "medium": 3, "high": 4}[level]
    instance["constraints"]["minimum_category_counts"] = {"culture": 1, "food": 1}
    if level == "high":
        instance["constraints"]["minimum_category_counts"] = {"culture": 2, "food": 2}
    instance["constraints"]["required_attraction_ids"] = selected[:1] if level != "high" else [selected[0], selected[-1]]
    instance["replica"] = replica
    # Independent numeric variation; dates and IDs are synthetic, not live availability.
    for a in instance["attractions"]:
        a["price"] += replica * (1 + int(a["id"].split("_A")[1].split("_")[0]) % 3)
    for h in instance["hotels"]:
        h["nightly_price"] += replica * 3
    instance["transport"]["default_travel_minutes"] = 20
    for j, slot in enumerate(slots):
        # The witness fits exact windows. One distractor is closed/too long.
        a = amap[selected[j]]
        a["open"], a["close"] = slot["start"], slot["end"]
        others = [amap[x] for x in slot["candidate_attraction_ids"] if x != selected[j]]
        bad = others[replica % len(others)]
        if (j + replica) % 2:
            bad["duration_minutes"] = 150
        else:
            bad["open"] = "17:00"
        bad["price"] = max(1, bad["price"] - 8)
    # A real shared choice in adjacent same-day slots exercises uniqueness.
    mid = [s for s in slots if s["day"] == 2]
    if len(mid) == 2:
        shared_id = mid[0]["candidate_attraction_ids"][0] + "_SHARED"
        shared = {"id": shared_id, "name": "Synthetic shared museum", "category": "culture", "price": 8 + replica,
                  "duration_minutes": 90, "open": "08:30", "close": "18:00", "location_id": shared_id + "_L",
                  "eligible_slot_ids": [s["slot_id"] for s in mid]}
        instance["attractions"].append(shared)
        amap[shared_id] = shared
        for slot in mid: slot["candidate_attraction_ids"].append(shared_id)
    # Explicit asymmetric travel overrides constrain particular candidate sequences.
    overrides = []
    for left, right in zip(slots, slots[1:]):
        if left["day"] != right["day"]: continue
        li = next(x for x in left["candidate_attraction_ids"] if x != selected[slots.index(left)] and amap[x]["open"] != "17:00" and amap[x]["duration_minutes"] <= 120)
        rj = selected[slots.index(right)]
        overrides.append({"from": amap[li]["location_id"], "to": amap[rj]["location_id"],
                          "minutes": instance["constraints"]["maximum_travel_minutes_per_leg"] + 5})
    instance["transport"]["overrides"] = overrides
    witness = instance["ground_truth"]["witness"]
    cost, _ = witness_cost(instance, witness["hotel_id"], selected)
    witness["total_cost"] = cost
    instance["trip"]["budget"] = cost + {"low": 40, "medium": 15, "high": 0}[level]
    instance["ground_truth"]["infeasibility_mutation"] = None
    return instance


def make_infeasible(feasible: dict, mutation: str) -> dict:
    case = copy.deepcopy(feasible)
    case["expected_feasible"] = False
    case["ground_truth"]["witness"] = None
    amap = {a["id"]: a for a in case["attractions"]}
    if mutation == "budget":
        bound = minimum_cost(case)
        case["trip"]["budget"] = bound - 1
        case["ground_truth"]["reason"] = f"Budget {bound - 1} is below unconditional cost lower bound {bound}."
    elif mutation == "category":
        capacity = sum(any(amap[x]["category"] == "nature" for x in s["candidate_attraction_ids"]) for s in case["daily_slots"])
        case["constraints"]["minimum_category_counts"]["nature"] = capacity + 1
        case["ground_truth"]["reason"] = f"Nature requirement {capacity + 1} exceeds candidate-slot capacity {capacity}."
    elif mutation == "required_slot":
        first = case["daily_slots"][0]
        exclusive = [x for x in first["candidate_attraction_ids"] if len(amap[x]["eligible_slot_ids"]) == 1]
        # Choose two legal exclusive values where possible, otherwise including an illegal
        # value is itself a documented no-legal-slot proof; keep the exclusive conflict.
        legal = [x for x in exclusive if amap[x]["open"] <= first["start"] and amap[x]["close"] >= first["end"] and amap[x]["duration_minutes"] <= 120]
        conflict = (legal + [x for x in exclusive if x not in legal])[:2]
        case["constraints"]["required_attraction_ids"] = list(dict.fromkeys(case["constraints"]["required_attraction_ids"] + conflict))
        case["ground_truth"]["reason"] = "Two required options are exclusive to the same single-choice slot: " + ", ".join(conflict)
    else: raise ValueError(mutation)
    case["ground_truth"]["infeasibility_mutation"] = mutation
    return case


def generate() -> dict:
    cases = []
    for duration_index, duration in enumerate((3, 5, 7)):
        for level_index, level in enumerate(("low", "medium", "high")):
            for replica in (0, 1):
                base = strengthen(make_base_case(duration_index * 3 + level_index, duration, level), replica)
                base["pair_id"] = f"P{duration}_{level}_{replica}"
                base["ground_truth"]["infeasibility_mutation"] = None
                cases.append(base)
                cases.extend(make_infeasible(base, m) for m in ("budget", "category", "required_slot"))
    random.Random(4263).shuffle(cases)
    for i, case in enumerate(cases, 1): case["instance_id"] = f"V2T{i:03d}"
    return {"benchmark_name": "CS4263 Group 17 crossed travel CSP", "dataset_version": "2.0.0",
            "generated_date": "2026-11-07", "data_notice": "Fixed synthetic prices, venues and schedules.",
            "design": {"durations_days": [3, 5, 7], "constraint_loads": ["low", "medium", "high"],
                       "base_replicas_per_cell": 2, "variants_per_base": ["feasible", "budget", "category", "required_slot"],
                       "total_instances": 72, "feasible_instances": 18, "infeasible_instances": 54,
                       "note": "Variants share a base; report feasible and infeasible accuracy separately. Labels describe intended constraint load, not empirically validated hardness."},
            "instances": cases}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("benchmark.json"))
    args = parser.parse_args()
    data = generate()
    args.output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(data['instances'])} crossed instances to {args.output}")


if __name__ == "__main__": main()
