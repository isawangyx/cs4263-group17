#!/usr/bin/env python3
"""Independent score-only validation. Never repairs or generates an itinerary."""
from __future__ import annotations
import argparse
from collections import Counter
from project_common import hhmm,jsonl_read,jsonl_write,load_benchmark


def validate(instance,output):
    violations=[]
    def add(category,detail):violations.append({'category':category,'detail':detail})
    expected=instance['expected_feasible'];status=output.get('status') if isinstance(output,dict) else None
    def score(cost=None,utility=0):
        return {'hard_constraint_pass':not violations and status in ('FEASIBLE','INFEASIBLE'),
                'correct_feasibility_classification':status in ('FEASIBLE','INFEASIBLE') and (status=='FEASIBLE')==expected,
                'violation_count':len(violations),'violations':violations,'computed_total_cost':cost,'utility_score':utility}
    if not isinstance(output,dict):add('unparseable_output','Expected a JSON object.');return score()
    if status not in ('FEASIBLE','INFEASIBLE'):add('invalid_status','Expected FEASIBLE or INFEASIBLE.');return score()
    if status=='INFEASIBLE':
        if expected:add('false_infeasible_claim','A verified feasible witness exists.')
        return score()
    if not expected:add('false_feasible_claim','This instance has a construction proof of infeasibility.')
    c=instance['constraints'];amap={a['id']:a for a in instance['attractions']};smap={s['slot_id']:s for s in instance['daily_slots']}
    maps=[{x['id']:x for x in instance['flights']['outbound']},{x['id']:x for x in instance['flights']['return']},{x['id']:x for x in instance['hotels']}]
    choices=[]
    for field,options in zip(('outbound_flight_id','return_flight_id','hotel_id'),maps):
        identifier=output.get(field);item=options.get(identifier) if isinstance(identifier,str) else None
        if item is None:add('invalid_'+field,str(identifier))
        choices.append(item)
    fo,fr,h=choices
    if h and h['rating']<c['minimum_hotel_rating']:add('hotel_rating','Hotel is below the minimum rating.')
    schedule=output.get('schedule')
    if not isinstance(schedule,list):add('invalid_schedule','Schedule must be an array.');schedule=[]
    entries={};selected={}
    for entry in schedule:
        if not isinstance(entry,dict):add('invalid_schedule_entry','Entry must be an object.');continue
        sid=entry.get('slot_id');aid=entry.get('attraction_id')
        if not isinstance(sid,str) or sid not in smap:add('invalid_slot_id',str(sid));continue
        entries.setdefault(sid,[]).append(aid)
    for sid,s in smap.items():
        values=entries.get(sid,[])
        if len(values)!=1:add('slot_cardinality',f'{sid} has {len(values)} choices.');continue
        aid=values[0]
        if not isinstance(aid,str) or aid not in amap:add('hallucinated_attraction',str(aid));continue
        a=amap[aid];selected[sid]=aid
        if aid not in s['candidate_attraction_ids'] or sid not in a['eligible_slot_ids']:add('slot_ineligible',f'{aid} in {sid}')
        if hhmm(a['open'])>hhmm(s['start']) or hhmm(a['close'])<hhmm(s['end']):add('opening_hours',f'{aid} is closed during {sid}.')
        if a['duration_minutes']>hhmm(s['end'])-hhmm(s['start']):add('duration',f'{aid} exceeds {sid}.')
    if len(set(selected.values()))!=len(selected):add('duplicate_attraction','Attractions must be unique.')
    counts=Counter(amap[a]['category'] for a in selected.values())
    for cat,n in c['minimum_category_counts'].items():
        if counts[cat]<n:add('category_minimum',f'{cat}: {counts[cat]} < {n}')
    if not set(c['required_attraction_ids'])<=set(selected.values()):add('missing_required_attraction','Required attraction omitted.')
    slots=sorted(instance['daily_slots'],key=lambda s:(s['day'],hhmm(s['start'])))
    if fo and hhmm(fo['arrive'])+c['arrival_buffer_minutes']>hhmm(slots[0]['start']):add('arrival_buffer','First slot starts too soon.')
    if fr and hhmm(slots[-1]['end'])+c['departure_buffer_minutes']>hhmm(fr['depart']):add('departure_buffer','Last slot ends too late.')
    # Recompute chronological transfers independently of the search implementation.
    overrides={(o['from'],o['to']):o['minutes'] for o in instance['transport'].get('overrides',[])}
    for left,right in zip(slots,slots[1:]):
        if left['day']!=right['day']:continue
        if hhmm(left['end'])>hhmm(right['start']):add('slot_overlap','Activity slots overlap.')
        if left['slot_id'] not in selected or right['slot_id'] not in selected:continue
        l1=amap[selected[left['slot_id']]]['location_id'];l2=amap[selected[right['slot_id']]]['location_id']
        t=0 if l1==l2 else overrides.get((l1,l2),instance['transport']['default_travel_minutes'])
        if t>c['maximum_travel_minutes_per_leg']:add('travel_time',f'{l1} to {l2}: {t} exceeds limit.')
        if hhmm(left['end'])+t>hhmm(right['start']):add('transfer_gap',f'Transfer does not fit before {right["slot_id"]}.')
    cost=None
    if fo and fr and h and len(selected)==len(smap) and all(len(v)==1 for v in entries.values()):
        cost=fo['price']+fr['price']+h['nightly_price']*(instance['trip']['duration_days']-1)+sum(amap[a]['price'] for a in selected.values())+instance['transport']['daily_pass_price']*instance['trip']['duration_days']
        if cost>instance['trip']['budget']:add('budget',f'{cost} exceeds {instance["trip"]["budget"]}.')
        if type(output.get('declared_total_cost')) is not int or output['declared_total_cost']!=cost:add('arithmetic_error',f'Declared {output.get("declared_total_cost")}; computed {cost}.')
    utility=sum(instance['preferences']['utility_weights']['preferred_category' if amap[a]['category'] in instance['preferences']['preferred_categories'] else 'non_preferred_category'] for a in selected.values())
    return score(cost,utility)


def main():
    p=argparse.ArgumentParser();p.add_argument('--benchmark',default='benchmark.json');p.add_argument('--inputs',required=True);p.add_argument('--output',required=True);args=p.parse_args()
    instances={x['instance_id']:x for x in load_benchmark(args.benchmark)['instances']};rows=[]
    for record in jsonl_read(args.inputs):
        if record['instance_id'] not in instances:raise ValueError('Output belongs to a different benchmark: '+record['instance_id'])
        rows.append({**record,**validate(instances[record['instance_id']],record.get('raw_output'))})
    jsonl_write(args.output,rows);print(f'Validated {len(rows)} outputs: {sum(x["hard_constraint_pass"] for x in rows)} complete passes.')
if __name__=='__main__':main()
