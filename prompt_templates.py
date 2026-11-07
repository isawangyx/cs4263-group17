"""Version 2.0: matched output schema and cumulative prompt safeguards."""
import json
COMMON_OUTPUT='''Return only a JSON object with status (FEASIBLE or INFEASIBLE), outbound_flight_id,
return_flight_id, hotel_id, schedule (array of {slot_id, attraction_id}), declared_total_cost
(integer), and verification_notes (array of concise strings).
For infeasible inputs use empty IDs, empty schedule, cost 0 and a brief conflict explanation.
Use only supplied IDs. The same attraction cannot be used twice. Travel overrides are
DIRECTIONAL from/to location IDs; otherwise use default_travel_minutes (same location: 0).
Check both the per-leg travel limit and the time gap between consecutive same-day slots.
Solve directly using reasoning from this JSON. Do not use tools, write or execute code,
search the filesystem, access other cases, or call any solver or validator.'''
STRUCTURED='''Before answering, account for every hard constraint: flight buffers, hotel rating,
slot cardinality, uniqueness, eligibility, opening hours, duration, category minima,
required attractions, directional travel times, transfer gaps and budget.
Keep a day-by-day timing table and itemized budget ledger internally.'''
VERIFICATION='''After a first draft, separately question each constraint family and recalculate
all costs from the supplied values. Check that each chosen identifier exists and each
required option occurs exactly once. Revise the draft once when any check fails.
This is a single-response self-check; return only the final answer and concise check notes.'''
def build_prompt(instance,condition):
    if condition not in ('B0','B1','B2'):raise ValueError(condition)
    instructions='Create a complete valid itinerary, or report infeasible if no valid itinerary exists.\n'+COMMON_OUTPUT
    if condition in ('B1','B2'):instructions+='\n'+STRUCTURED
    if condition=='B2':instructions+='\n'+VERIFICATION
    return instructions+'\n\nINSTANCE JSON:\n'+json.dumps(instance,separators=(',',':'))
