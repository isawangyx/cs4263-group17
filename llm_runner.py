#!/usr/bin/env python3
"""Independent, tool-free model trials with append-only results and frozen manifests."""
from __future__ import annotations
import argparse,concurrent.futures,hashlib,json,os,random,subprocess,tempfile,time,urllib.request
from datetime import datetime,timezone
from pathlib import Path
from project_common import ITINERARY_SCHEMA,jsonl_read
from prompt_templates import build_prompt

def digest(data):return hashlib.sha256(data).hexdigest()
def parse_text(text):
    # Parsing only; no itinerary construction, selection, or repair.
    return json.loads(text)

def call_codex(model,prompt,reasoning,isolation):
    command=['codex','exec','--ignore-user-config','--ephemeral','--skip-git-repo-check','-C',isolation,'-s','read-only',
             '--disable','shell_tool','--disable','apps','--disable','plugins','--disable','multi_agent',
             '--disable','browser_use','--disable','computer_use','-c','web_search="disabled"',
             '-c','features.skip_host_skill_discovery=true','-c','agents.enabled=false',
             '-c',f'model_reasoning_effort="{reasoning}"','-m',model,'--json','-']
    done=subprocess.run(command,input=prompt,text=True,capture_output=True,timeout=240)
    events=[]
    for line in done.stdout.splitlines():
        try:events.append(json.loads(line))
        except json.JSONDecodeError:pass
    messages=[];usage={};thread=None;tool_used=False
    for e in events:
        if e.get('type')=='thread.started':thread=e.get('thread_id')
        if e.get('type')=='turn.completed':usage=e.get('usage',{})
        if e.get('type')=='item.completed':
            item=e.get('item',{})
            if item.get('type')=='agent_message':messages.append(item.get('text',''))
            if item.get('type') in ('command_execution','mcp_tool_call','web_search','file_change'):tool_used=True
    text=messages[-1] if messages else ''
    return text,{'events':events,'stderr':done.stderr,'exit_code':done.returncode},usage,thread,tool_used

def call_api(model,prompt,reasoning):
    body={'model':model,'input':prompt,'reasoning':{'effort':reasoning},'max_output_tokens':6000,
          'text':{'format':{'type':'json_schema','name':'travel_itinerary','strict':True,'schema':ITINERARY_SCHEMA}}}
    req=urllib.request.Request('https://api.openai.com/v1/responses',data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+os.environ['OPENAI_API_KEY'],'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=240) as response:payload=json.load(response)
    text=''.join(c.get('text','') for x in payload.get('output',[]) if x.get('type')=='message' for c in x.get('content',[]) if c.get('type')=='output_text')
    return text,payload,payload.get('usage',{}),payload.get('id'),False

def main():
    p=argparse.ArgumentParser();p.add_argument('--inputs',default='llm_inputs.jsonl');p.add_argument('--output',default='llm_independent_outputs.jsonl');p.add_argument('--backend',choices=['api','codex'],default='api')
    p.add_argument('--model',default=os.environ.get('OPENAI_MODEL'));p.add_argument('--reasoning',default='medium');p.add_argument('--repetitions',type=int,default=2);p.add_argument('--workers',type=int,default=6);p.add_argument('--conditions',nargs='+',default=['B0','B1','B2'])
    args=p.parse_args()
    if not args.model:raise SystemExit('Specify --model (or OPENAI_MODEL).')
    if args.backend=='api' and not os.environ.get('OPENAI_API_KEY'):raise SystemExit('OPENAI_API_KEY is not configured.')
    inputs=jsonl_read(args.inputs)
    if any('ground_truth' in x or 'expected_feasible' in x or 'pair_id' in x for x in inputs):raise SystemExit('Evaluation metadata leaked into model inputs.')
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    manifest_path=out.with_suffix('.manifest.json');raw_dir=out.parent/(out.stem+'_raw');raw_dir.mkdir(exist_ok=True)
    settings={'inputs_sha256':digest(Path(args.inputs).read_bytes()),'prompts_sha256':digest(Path('prompt_templates.py').read_bytes()),'backend':args.backend,'model':args.model,'reasoning':args.reasoning,'repetitions':args.repetitions,'conditions':args.conditions,'instances':len(inputs),'order_seed':42632,'temperature':'provider default; not set','tool_access':'disabled; reject trial if tool use appears in events'}
    if manifest_path.exists():
        if json.loads(manifest_path.read_text())['settings']!=settings:raise SystemExit('Manifest mismatch: use a new output path for changed inputs/settings.')
    else:manifest_path.write_text(json.dumps({'created_utc':datetime.now(timezone.utc).isoformat(),'settings':settings},indent=2)+'\n')
    existing=jsonl_read(out)
    if any(x.get('provenance')!='independent_model_trial' for x in existing):raise SystemExit('Refusing to mix independent results with pilot fixtures.')
    done={(r['instance_id'],r['condition'],r['trial_id']) for r in existing}
    tasks=[(i,c,t) for t in range(1,args.repetitions+1) for c in args.conditions for i in inputs]
    random.Random(42632).shuffle(tasks);tasks=[x for x in tasks if (x[0]['instance_id'],x[1],x[2]) not in done]
    isolation=tempfile.mkdtemp(prefix='cs4263-no-labels-')
    def run(task):
        i,c,t=task;stem=f'{i["instance_id"]}_{c}_{t}';prompt=build_prompt(i,c)
        record={'instance_id':i['instance_id'],'condition':c,'trial_id':t,'method':'llm','model':args.model,'reasoning':args.reasoning,'backend':args.backend,'provenance':'independent_model_trial','prompt_sha256':digest(prompt.encode()),'input_sha256':digest(json.dumps(i,sort_keys=True).encode()),'raw_output':None,'usage':{},'response_id':None,'started_utc':datetime.now(timezone.utc).isoformat()}
        started=time.perf_counter()
        try:
            text,raw,usage,response_id,tool_used=(call_codex(args.model,prompt,args.reasoning,isolation) if args.backend=='codex' else call_api(args.model,prompt,args.reasoning))
            # Preserve complete provider/CLI response BEFORE parsing or validation.
            (raw_dir/(stem+'.json')).write_text(json.dumps({'prompt':prompt,'response':raw,'output_text':text},ensure_ascii=False,indent=2)+'\n')
            record.update(usage=usage,response_id=response_id,raw_text=text,raw_response_file=str(raw_dir/(stem+'.json')),tool_used=tool_used)
            if tool_used:raise ValueError('Tool use invalidates the direct-reasoning trial.')
            record['raw_output']=parse_text(text)
        except Exception as error:record['error']=type(error).__name__+': '+str(error)
        record['latency_seconds']=time.perf_counter()-started
        return record
    print(f'{len(tasks)} trials remaining; backend={args.backend}, model={args.model}, repetitions={args.repetitions}',flush=True)
    with out.open('a') as handle,concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for n,record in enumerate(pool.map(run,tasks),1):
            handle.write(json.dumps(record,separators=(',',':'))+'\n');handle.flush()
            if n%6==0 or record.get('error'):print(f'{n}/{len(tasks)}: {record["instance_id"]} {record["condition"]} trial {record["trial_id"]}: '+('ERROR '+record['error'] if record.get('error') else 'saved'),flush=True)
if __name__=='__main__':main()
