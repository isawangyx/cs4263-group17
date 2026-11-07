#!/usr/bin/env python3
"""Export candidate data while hiding all construction and evaluation metadata."""
import copy,json,sys
from pathlib import Path

def public_instance(original):
    instance=copy.deepcopy(original)
    for field in ('ground_truth','expected_feasible','pair_id','difficulty','replica','dataset_version'):instance.pop(field,None)
    return instance

def main():
    source=Path(sys.argv[1] if len(sys.argv)>1 else 'benchmark.json');target=Path(sys.argv[2] if len(sys.argv)>2 else 'llm_inputs.jsonl')
    data=json.loads(source.read_text());target.write_text(''.join(json.dumps(public_instance(x),separators=(',',':'))+'\n' for x in data['instances']))
    print(f'Exported {len(data["instances"])} label-free cases.')
if __name__=='__main__':main()
