#!/usr/bin/env python3
"""Regression coverage for guarantees, model-output failures, and experiment isolation."""
import copy,itertools,json,random,tempfile,unittest
from pathlib import Path
from csp_solver import solve,required_matching
from export_llm_inputs import public_instance
from project_common import load_benchmark
from validator import validate

def tiny():
    return {'instance_id':'test','dataset_version':'test','expected_feasible':True,'trip':{'duration_days':3,'budget':1000},
      'flights':{'outbound':[{'id':'F','arrive':'07:00','price':10}],'return':[{'id':'R','depart':'23:00','price':10}]},
      'hotels':[{'id':'H','rating':4,'nightly_price':10}],
      'daily_slots':[{'slot_id':'S1','day':2,'start':'09:00','end':'10:00','candidate_attraction_ids':['A','B','C']}, {'slot_id':'S2','day':2,'start':'10:30','end':'11:30','candidate_attraction_ids':['A','B','C']}],
      'attractions':[{'id':x,'price':10+i,'category':'culture' if i%2==0 else 'food','duration_minutes':60,'open':'08:00','close':'18:00','location_id':x,'eligible_slot_ids':['S1','S2']} for i,x in enumerate('ABC')],
      'transport':{'default_travel_minutes':20,'daily_pass_price':0,'overrides':[]},
      'constraints':{'arrival_buffer_minutes':90,'departure_buffer_minutes':120,'minimum_hotel_rating':3,'minimum_category_counts':{},'required_attraction_ids':[],'maximum_travel_minutes_per_leg':30},
      'preferences':{'preferred_categories':['culture'],'utility_weights':{'preferred_category':2,'non_preferred_category':1}}}

class ProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.instances=load_benchmark('benchmark.json')['instances']
    def test_all_crossed_cases(self):
        for x in self.instances:
            with self.subTest(id=x['instance_id']):self.assertTrue(validate(x,solve(x))['hard_constraint_pass'])
    def test_travel_limit_rejects(self):
        x=tiny();x['transport']['default_travel_minutes']=31
        self.assertEqual(solve(x)['status'],'INFEASIBLE')
    def test_shared_required_values_are_feasible(self):
        x=tiny();x['constraints']['required_attraction_ids']=['A','B']
        p=solve(x);self.assertEqual(p['status'],'FEASIBLE');self.assertTrue(validate(x,p)['hard_constraint_pass'])
    def test_hall_conflict(self):
        self.assertFalse(required_matching({'A','B','C'},{'S1':['A','B','C'],'S2':['A','B','C']}))
    def test_transfer_gap_independent_of_leg_limit(self):
        x=tiny();x['transport']['default_travel_minutes']=40;x['constraints']['maximum_travel_minutes_per_leg']=60
        self.assertEqual(solve(x)['status'],'INFEASIBLE')
    def test_directional_override(self):
        x=tiny();x['constraints']['required_attraction_ids']=['A','B'];x['daily_slots'][0]['candidate_attraction_ids']=['A'];x['daily_slots'][1]['candidate_attraction_ids']=['B'];x['transport']['overrides']=[{'from':'A','to':'B','minutes':45}]
        self.assertEqual(solve(x)['status'],'INFEASIBLE')
        x['transport']['overrides']=[{'from':'B','to':'A','minutes':45}]
        self.assertEqual(solve(x)['status'],'FEASIBLE')
    def test_validator_detects_travel(self):
        x=tiny();p=solve(x);x['transport']['default_travel_minutes']=31
        self.assertIn('travel_time',{v['category'] for v in validate(x,p)['violations']})
    def test_validator_malformed_values_never_crash(self):
        x=tiny();p=solve(x)
        for field in ('hotel_id','outbound_flight_id','return_flight_id'):
            for bad in ([],{},None,True):
                q=copy.deepcopy(p);q[field]=bad;self.assertFalse(validate(x,q)['hard_constraint_pass'])
        for bad in ([],{},None,17):
            q=copy.deepcopy(p);q['schedule'][0]['attraction_id']=bad;self.assertFalse(validate(x,q)['hard_constraint_pass'])
            q=copy.deepcopy(p);q['schedule'][0]['slot_id']=bad;self.assertFalse(validate(x,q)['hard_constraint_pass'])
        for bad in (None,[],3,'bad'):
            self.assertFalse(validate(x,bad)['hard_constraint_pass'])
    def test_validator_arithmetic_and_omission(self):
        x=tiny();p=solve(x);p['declared_total_cost']+=1
        self.assertIn('arithmetic_error',{v['category'] for v in validate(x,p)['violations']})
        p=solve(x);p['schedule'].pop();self.assertFalse(validate(x,p)['hard_constraint_pass'])
    def test_false_infeasible_and_invalid_status(self):
        for output in ({'status':'INFEASIBLE'},{'status':'garbage'}):self.assertFalse(validate(tiny(),output)['hard_constraint_pass'])
    def test_unary_hours_duration_and_reciprocal_eligibility(self):
        for change,value in (('open','12:00'),('duration_minutes',90),('eligible_slot_ids',[])):
            x=tiny()
            for a in x['attractions']:a[change]=value
            self.assertEqual(solve(x)['status'],'INFEASIBLE')
    def test_no_evaluation_metadata_in_export(self):
        for x in self.instances:
            self.assertFalse(set(public_instance(x))&{'ground_truth','expected_feasible','difficulty','pair_id','replica'})
    def test_small_random_cases_against_exhaustive_enumeration(self):
        rng=random.Random(4263)
        for trial in range(80):
            x=tiny();x['trip']['budget']=rng.randint(40,90);x['constraints']['required_attraction_ids']=rng.sample(list('ABC'),rng.randrange(4))
            x['constraints']['minimum_category_counts']={'food':rng.randrange(3)}
            x['transport']['overrides']=[{'from':a,'to':b,'minutes':rng.choice([10,20,35,60])} for a in 'ABC' for b in 'ABC' if a!=b]
            found=False
            for a,b in itertools.product('ABC',repeat=2):
                p={'status':'FEASIBLE','outbound_flight_id':'F','return_flight_id':'R','hotel_id':'H','schedule':[{'slot_id':'S1','attraction_id':a},{'slot_id':'S2','attraction_id':b}],'declared_total_cost':40+next(v['price'] for v in x['attractions'] if v['id']==a)+next(v['price'] for v in x['attractions'] if v['id']==b)}
                if validate(x,p)['hard_constraint_pass']:found=True;break
            with self.subTest(trial=trial):self.assertEqual(solve(x)['status']=='FEASIBLE',found)
if __name__=='__main__':unittest.main()
