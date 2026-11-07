#!/usr/bin/env python3
"""Complete finite CSP search; no evaluation labels or witnesses participate."""
from __future__ import annotations
import argparse
import time
from collections import Counter
from project_common import hhmm, jsonl_write, load_benchmark


def compatible_flights(instance):
    c = instance['constraints']; slots = sorted(instance['daily_slots'], key=lambda s: (s['day'], hhmm(s['start'])))
    return ([f for f in instance['flights']['outbound'] if hhmm(f['arrive']) + c['arrival_buffer_minutes'] <= hhmm(slots[0]['start'])],
            [f for f in instance['flights']['return'] if hhmm(slots[-1]['end']) + c['departure_buffer_minutes'] <= hhmm(f['depart'])])


def required_matching(required, domains):
    """Necessary injective assignment of remaining required values to slots (Hall)."""
    matched = {}
    def augment(a, visited):
        for slot, values in domains.items():
            if a not in values or slot in visited: continue
            visited.add(slot)
            if slot not in matched or augment(matched[slot], visited):
                matched[slot] = a
                return True
        return False
    return all(augment(a, set()) for a in sorted(required))


def solve(instance):
    started = time.perf_counter(); nodes = 0; backtracks = 0
    c = instance['constraints']; attractions = {a['id']: a for a in instance['attractions']}
    slots = sorted(instance['daily_slots'], key=lambda s: (s['day'], hhmm(s['start'])))
    smap = {s['slot_id']: s for s in slots}
    required = set(c['required_attraction_ids']); minima = c['minimum_category_counts']
    out, ret = compatible_flights(instance)
    hotels = [h for h in instance['hotels'] if h['rating'] >= c['minimum_hotel_rating']]
    domains = {s['slot_id']: [a_id for a_id in s['candidate_attraction_ids'] if a_id in attractions
               and s['slot_id'] in attractions[a_id]['eligible_slot_ids']
               and hhmm(attractions[a_id]['open']) <= hhmm(s['start'])
               and hhmm(attractions[a_id]['close']) >= hhmm(s['end'])
               and attractions[a_id]['duration_minutes'] <= hhmm(s['end']) - hhmm(s['start'])] for s in slots}
    neighbors = {s['slot_id']: [] for s in slots}
    edges = []
    for left, right in zip(slots, slots[1:]):
        if left['day'] == right['day']:
            edges.append((left['slot_id'], right['slot_id']))
            neighbors[left['slot_id']].append(right['slot_id']); neighbors[right['slot_id']].append(left['slot_id'])
    travel = {(o['from'], o['to']): o['minutes'] for o in instance['transport'].get('overrides', [])}
    def compatible(s1, a1, s2, a2):
        if (s1, s2) not in edges: s1, a1, s2, a2 = s2, a2, s1, a1
        l1 = attractions[a1]['location_id']; l2 = attractions[a2]['location_id']
        minutes = 0 if l1 == l2 else travel.get((l1, l2), instance['transport']['default_travel_minutes'])
        return minutes <= c['maximum_travel_minutes_per_leg'] and hhmm(smap[s1]['end']) + minutes <= hhmm(smap[s2]['start'])
    def finish(plan, reason=None):
        if plan is None:
            plan = {'status':'INFEASIBLE','outbound_flight_id':'','return_flight_id':'','hotel_id':'',
                    'schedule':[], 'declared_total_cost':0, 'verification_notes':[reason or 'Complete search exhausted all legal assignments.']}
        plan.update(search_nodes=nodes, backtracks=backtracks, latency_seconds=time.perf_counter()-started)
        return plan
    if not out or not ret or not hotels or not all(domains.values()): return finish(None, 'An option domain is empty after unary filtering.')
    if not required_matching(required, domains): return finish(None, 'Required attractions admit no injective assignment to legal slots.')
    for category, minimum in minima.items():
        if sum(any(attractions[a]['category'] == category for a in d) for d in domains.values()) < minimum:
            return finish(None, f'Category {category} exceeds selectable-slot capacity.')
    preferred = set(instance['preferences']['preferred_categories'])
    for fo in sorted(out, key=lambda x:x['price']):
        for fr in sorted(ret, key=lambda x:x['price']):
            for h in sorted(hotels, key=lambda x:x['nightly_price']):
                fixed = fo['price'] + fr['price'] + h['nightly_price']*(instance['trip']['duration_days']-1) + instance['transport']['daily_pass_price']*instance['trip']['duration_days']
                selected = {}; used = set(); counts = Counter()
                def search(cost):
                    nonlocal nodes, backtracks
                    remaining = {sid:[a for a in vals if a not in used and all(n not in selected or compatible(sid,a,n,selected[n]) for n in neighbors[sid])]
                                 for sid,vals in domains.items() if sid not in selected}
                    if any(not d for d in remaining.values()): backtracks+=1; return None
                    if fixed+cost+sum(min(attractions[a]['price'] for a in d) for d in remaining.values()) > instance['trip']['budget']:
                        backtracks+=1; return None
                    if not required_matching(required-used, remaining): backtracks+=1; return None
                    if any(counts[cat]+sum(any(attractions[a]['category']==cat for a in d) for d in remaining.values()) < m for cat,m in minima.items()):
                        backtracks+=1; return None
                    if not remaining:
                        return {'status':'FEASIBLE', 'outbound_flight_id':fo['id'],'return_flight_id':fr['id'],'hotel_id':h['id'],
                                'schedule':[{'slot_id':s['slot_id'],'attraction_id':selected[s['slot_id']]} for s in slots],
                                'declared_total_cost':fixed+cost,'verification_notes':['Complete assignment satisfies the encoded finite CSP.']}
                    # Dynamic MRV; degree-style tie-break counts remaining interactions.
                    sid=min(remaining,key=lambda x:(len(remaining[x]),-sum(n in remaining for n in neighbors[x]),-sum(a in required for a in remaining[x]),x))
                    def value_key(a):
                        support=sum(sum(v != a and (n not in neighbors[sid] or compatible(sid,a,n,v)) for v in vals) for n,vals in remaining.items() if n!=sid)
                        return (a not in required, -support, attractions[a]['category'] not in preferred, attractions[a]['price'], a)
                    for a in sorted(remaining[sid],key=value_key):
                        nodes+=1;selected[sid]=a;used.add(a);cat=attractions[a]['category'];counts[cat]+=1
                        result=search(cost+attractions[a]['price'])
                        if result is not None:return result
                        counts[cat]-=1;used.remove(a);del selected[sid]
                    backtracks+=1;return None
                result=search(0)
                if result is not None:return finish(result)
    return finish(None)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--benchmark',default='benchmark.json');parser.add_argument('--output',default='classical_outputs.jsonl');parser.add_argument('--repetitions',type=int,default=10)
    args=parser.parse_args();rows=[]
    for instance in load_benchmark(args.benchmark)['instances']:
        plans=[solve(instance) for _ in range(args.repetitions)]
        p=plans[0]
        rows.append({'instance_id':instance['instance_id'],'dataset_version':instance['dataset_version'],'method':'classical_csp','condition':'classical','raw_output':p,
                     'latency_seconds':sum(x['latency_seconds'] for x in plans)/len(plans),'timing_samples_seconds':[x['latency_seconds'] for x in plans],
                     'search_nodes':p['search_nodes'],'backtracks':p['backtracks']})
    jsonl_write(args.output,rows);print(f'Wrote {len(rows)} classical outputs ({args.repetitions} timing repetitions each).')
if __name__=='__main__':main()
