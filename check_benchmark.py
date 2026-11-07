#!/usr/bin/env python3
"""Check crossed design, one-field mutations, witness validity, and construction proofs."""
import copy,json,sys
from collections import Counter,defaultdict
from pathlib import Path
from validator import validate

def differences(a,b,path=''):
    if isinstance(a,dict) and isinstance(b,dict):
        return [x for k in set(a)|set(b) for x in differences(a.get(k),b.get(k),path+'.'+k)]
    return [] if a==b else [path]

def main():
    b=json.loads(Path(sys.argv[1] if len(sys.argv)>1 else 'benchmark.json').read_text());cases=b['instances'];groups=defaultdict(list)
    assert len(cases)==72 and len({x['instance_id'] for x in cases})==72
    cells=Counter((x['trip']['duration_days'],x['difficulty'],x['ground_truth']['infeasibility_mutation'] or 'feasible') for x in cases)
    assert len(cells)==36 and set(cells.values())=={2}
    for x in cases:groups[x['pair_id']].append(x)
    assert len(groups)==18
    for pair,variants in groups.items():
        assert len(variants)==4
        base=next(x for x in variants if x['expected_feasible']);w=base['ground_truth']['witness']
        output={'status':'FEASIBLE','outbound_flight_id':w['outbound_flight_id'],'return_flight_id':w['return_flight_id'],'hotel_id':w['hotel_id'],'schedule':[{'slot_id':s['slot_id'],'attraction_id':a} for s,a in zip(base['daily_slots'],w['attraction_ids_by_slot'])],'declared_total_cost':w['total_cost']}
        assert validate(base,output)['hard_constraint_pass'],pair
        amap={a['id']:a for a in base['attractions']}
        for x in variants:
            if x['expected_feasible']:continue
            ds=[d for d in differences(base,x) if not d.startswith(('.instance_id','.ground_truth','.expected_feasible'))]
            mutation=x['ground_truth']['infeasibility_mutation']
            target={'budget':'.trip.budget','category':'.constraints.minimum_category_counts.nature','required_slot':'.constraints.required_attraction_ids'}[mutation]
            assert ds==[target],(pair,ds)
            if mutation=='budget':
                lower=min(f['price'] for f in x['flights']['outbound'])+min(f['price'] for f in x['flights']['return'])+min(h['nightly_price'] for h in x['hotels'])*(x['trip']['duration_days']-1)+sum(min(amap[a]['price'] for a in s['candidate_attraction_ids']) for s in x['daily_slots'])+x['transport']['daily_pass_price']*x['trip']['duration_days']
                assert x['trip']['budget']<lower
            elif mutation=='category':
                capacity=sum(any(amap[a]['category']=='nature' for a in s['candidate_attraction_ids']) for s in x['daily_slots'])
                assert x['constraints']['minimum_category_counts']['nature']>capacity
            else:
                required=set(x['constraints']['required_attraction_ids'])
                assert any(len([a for a in s['candidate_attraction_ids'] if a in required and amap[a]['eligible_slot_ids']==[s['slot_id']]])>=2 for s in x['daily_slots'])
    print('PASS: 72 cases, 18 feasible bases, all 3 contradiction types at every duration/load; 2 replicas; witnesses and one-field proofs verified.')
if __name__=='__main__':main()
