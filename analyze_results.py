#!/usr/bin/env python3
"""Reproducible descriptive and paired cluster analysis of measured outputs."""
import argparse,csv,json,random,statistics
from collections import Counter,defaultdict
from pathlib import Path
from project_common import jsonl_read,load_benchmark


def mean(xs):return statistics.fmean(xs) if xs else None

def cluster_interval(rows,metric='hard_constraint_pass',samples=2000):
    groups=defaultdict(list)
    for r in rows:groups[r['pair_id']].append(float(r[metric]))
    if len(groups)<2:return [None,None]
    clusters=list(groups.values());rng=random.Random(4263);est=[]
    for _ in range(samples):
        drawn=[v for _ in clusters for v in rng.choice(clusters)];est.append(statistics.fmean(drawn))
    est.sort();return [est[int(.025*samples)],est[int(.975*samples)-1]]

def summarise(rows):
    feasible=[r for r in rows if r['expected_feasible']];infeasible=[r for r in rows if not r['expected_feasible']]
    valid=[r for r in feasible if r['hard_constraint_pass']]
    return {'n':len(rows),'passes':sum(r['hard_constraint_pass'] for r in rows),'pass_rate':mean([r['hard_constraint_pass'] for r in rows]),
       'pass_cluster_95ci':cluster_interval(rows),'feasible_pass_rate':mean([r['hard_constraint_pass'] for r in feasible]),
       'infeasible_accuracy':mean([r['hard_constraint_pass'] for r in infeasible]),
       'balanced_accuracy':mean([mean([r['hard_constraint_pass'] for r in feasible]),mean([r['hard_constraint_pass'] for r in infeasible])]) if feasible and infeasible else None,
       'violations':sum(r['violation_count'] for r in rows),'violation_categories':dict(Counter(v['category'] for r in rows for v in r['violations'])),
       'mean_latency_seconds':mean([r['latency_seconds'] for r in rows if r.get('latency_seconds') is not None]),
       'mean_input_tokens':mean([r['usage'].get('input_tokens',0) for r in rows if r.get('usage')]),
       'mean_output_tokens':mean([r['usage'].get('output_tokens',0) for r in rows if r.get('usage')]),
       'mean_cost_valid_feasible':mean([r['computed_total_cost'] for r in valid]),'mean_utility_valid_feasible':mean([r['utility_score'] for r in valid]),
       'mean_nodes':mean([r['search_nodes'] for r in rows if 'search_nodes' in r]),'mean_backtracks':mean([r['backtracks'] for r in rows if 'backtracks' in r]),
       'generation_errors':sum(bool(r.get('error')) for r in rows),'tool_use_trials':sum(bool(r.get('tool_used')) for r in rows)}

def write_discussion(s, measured_rows):
    c=s['conditions'];rows=[r for r in measured_rows if r['condition'] != 'classical']
    def fmt(x):return f'{x:.2f}'
    parts=[f"Classical search passed {c['classical']['passes']}/72 cases, averaging {c['classical']['mean_nodes']:.2f} assignment nodes, {c['classical']['mean_backtracks']:.2f} backtracks and {c['classical']['mean_latency_seconds']*1000:.3f} ms per case over ten local timing repetitions. "+' '.join(f"{k} passed {c[k]['passes']}/144 model trials." for k in ('B0','B1','B2'))]
    failures=[r for r in rows if not r['hard_constraint_pass']]
    if failures:
     examples=[]
     for r in failures[:2]:
      detail='; '.join(v['detail'] for v in r['violations']).replace('_',r'\_')
      examples.append(f"{r['condition']} on {r['instance_id']} (trial {r['trial_id']}): {detail}")
     parts.append('Recorded failures include '+ ' '.join(examples)+'. These original outputs remain unchanged in the raw archive. A self-check instruction therefore supplies no correctness guarantee.')
    else:parts.append('No model trial failed the scorer. This is an observed ceiling, not evidence that these prompts guarantee correctness or that safeguards cannot help on harder tasks.')
    for k in ('B1','B2'):
     d=s['paired_safeguard_contrasts'][k+'-B0'];lo,hi=d['base_cluster_95ci']
     parts.append(f"{k} minus B0 has a paired pass-rate difference of {100*d['pass_rate_difference']:+.2f} percentage points (descriptive 95\\% base-cluster interval {100*lo:+.2f} to {100*hi:+.2f}).")
    parts.append('Mean operational model latency was '+', '.join(f"{c[k]['mean_latency_seconds']:.2f} s for {k}" for k in ('B0','B1','B2'))+'. '+ 'Mean input/output tokens were '+', '.join(f"{c[k]['mean_input_tokens']:.0f}/{c[k]['mean_output_tokens']:.0f} ({k})" for k in ('B0','B1','B2'))+'. These values include the CLI context and service overhead. The measured LLM path did not outperform local classical search on operational latency; this does not establish a general efficiency ranking for other planning settings.')
    parts.append('Among valid feasible plans, mean utility was '+', '.join(f"{c[k]['mean_utility_valid_feasible']:.2f} ({k})" for k in ('classical','B0','B1','B2'))+'. Utility and cost vary with first-feasible choices and are not proofs of optimality. Per-duration, per-load and per-contradiction outcomes are retained in the results CSV and summary. The short constructed contradictions are easier to reject than open-world plans are to build, so the feasibility-specific rates in Table~\\ref{tab:results} are essential.')
    parts.append(('B0 passes every observed trial, leaving no baseline errors for added safeguards to reduce. ' if c['B0']['pass_rate']==1 else 'The paired contrasts describe the measured safeguard effect on this configuration. ')+ 'Repeated contexts and raw provenance strengthen the comparison relative to the original fixture pilot, while modest base diversity and ceiling effects limit its precision. The full suite and all generation outcomes are included; no failure was repaired or excluded.')
    Path('results_discussion.tex').write_text('\n\n'.join(parts)+'\n')
    print('Generated final discussion:',sum(len(x.split()) for x in parts),'words.')

def main():
    p=argparse.ArgumentParser();p.add_argument('--benchmark',default='benchmark.json');p.add_argument('--classical',default='classical_scores.jsonl');p.add_argument('--llm',default='experiments/v2_llm_scores.jsonl');p.add_argument('--csv',default='results.csv');p.add_argument('--summary',default='RESULTS_SUMMARY.md');p.add_argument('--table',default='results_table.tex');args=p.parse_args()
    b=load_benchmark(args.benchmark);meta={r['instance_id']:r for r in b['instances']};rows=[]
    for record in jsonl_read(args.classical)+jsonl_read(args.llm):
        x=meta[record['instance_id']]
        if record.get('method')=='llm' and record.get('provenance')!='independent_model_trial':raise ValueError('Pilot fixture cannot enter independent analysis.')
        rows.append({**record,'duration_days':x['trip']['duration_days'],'difficulty':x['difficulty'],'variant':x['ground_truth']['infeasibility_mutation'] or 'feasible','expected_feasible':x['expected_feasible'],'pair_id':x['pair_id']})
    fields=['instance_id','pair_id','condition','trial_id','duration_days','difficulty','variant','expected_feasible','hard_constraint_pass','correct_feasibility_classification','violation_count','computed_total_cost','utility_score','latency_seconds','search_nodes','backtracks','model','backend']
    with open(args.csv,'w') as f:
        w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
    conditions={c:summarise([r for r in rows if r['condition']==c]) for c in ('classical','B0','B1','B2') if any(r['condition']==c for r in rows)}
    subgroups={}
    for field in ('duration_days','difficulty','variant'):
        subgroups[field]={str(value):{c:summarise([r for r in rows if r[field]==value and r['condition']==c]) for c in conditions if any(r[field]==value and r['condition']==c for r in rows)} for value in sorted({r[field] for r in rows},key=str)}
    lookup={(r['instance_id'],r.get('trial_id'),r['condition']):r for r in rows if r['condition']!='classical'}
    contrasts={}
    for c in ('B1','B2'):
        paired=[]
        for (iid,trial,condition),r in lookup.items():
            base=lookup.get((iid,trial,'B0'))
            if condition==c and base:
                paired.append({'pair_id':r['pair_id'],'delta':int(r['hard_constraint_pass'])-int(base['hard_constraint_pass'])})
        if paired:contrasts[c+'-B0']={'matched_trials':len(paired),'pass_rate_difference':mean([r['delta'] for r in paired]),'base_cluster_95ci':cluster_interval(paired,'delta')}
    summary={'dataset_version':b['dataset_version'],'base_clusters':18,'cases':72,'expected_trials_per_llm_condition':144,'conditions':conditions,'paired_safeguard_contrasts':contrasts,'subgroups':subgroups,'llm_trials':len(lookup),'complete':all(conditions.get(c,{}).get('n')==144 for c in ('B0','B1','B2'))}
    Path('analysis_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    def pct(x):return 'NA' if x is None else f'{100*x:.1f}%'
    lines=['# Measured results, dataset v2.0','',f'Independent trials saved and scored: {len(lookup)}/432. Complete: {summary["complete"]}.','', '| Condition | Passes | Pass rate | Feasible pass | Infeasible accuracy | Balanced accuracy | Mean seconds |','|---|---:|---:|---:|---:|---:|---:|']
    latex=['\\begin{table}[t]','\\centering','\\caption{Measured results on 72 cases. LLM conditions have two independent repetitions; time includes CLI/network overhead.}','\\label{tab:results}','\\begin{tabular}{lrrrr}','\\toprule','Condition & Passes & Feas. (\\%) & Infeas. (\\%) & Mean s \\\\','\\midrule']
    for c,x in conditions.items():
        lines.append(f'| {c} | {x["passes"]}/{x["n"]} | {pct(x["pass_rate"])} | {pct(x["feasible_pass_rate"])} | {pct(x["infeasible_accuracy"])} | {pct(x["balanced_accuracy"])} | {x["mean_latency_seconds"]:.4f} |')
        latex.append(f'{c} & {x["passes"]}/{x["n"]} & {100*x["feasible_pass_rate"]:.1f} & {100*x["infeasible_accuracy"]:.1f} & {x["mean_latency_seconds"]:.4f} \\\\')
    latex+=['\\bottomrule','\\end{tabular}','\\end{table}']
    lines+=['','## Interpretation boundaries','','The suite has 18 feasible and 54 infeasible cases. Always declaring infeasible scores 75% overall, so report feasible success and balanced accuracy alongside the overall rate. Variants share their base, and repetitions share an instance. Confidence intervals resample the 18 base clusters, not 432 independent problems. They are descriptive and have limited resolution. Classical times average 10 local runs per case. LLM elapsed times include process, service and network overhead; token totals include the CLI system context. No cost in dollars is inferred.','']
    for label,x in contrasts.items():lines.append(f'{label}: paired pass-rate difference {x["pass_rate_difference"]:+.3f}; 95% base-cluster interval {x["base_cluster_95ci"]}.')
    lines+=['','## Violation categories','']
    for c,x in conditions.items():lines.append(f'- {c}: {x["violation_categories"]}; generation errors {x["generation_errors"]}.')
    for field,values in subgroups.items():
        lines+=['',f'## Results by {field}','','| Group | Condition | Passes | Mean seconds |','|---|---|---:|---:|']
        for value,cs in values.items():
            for c,x in cs.items():lines.append(f'| {value} | {c} | {x["passes"]}/{x["n"]} | {x["mean_latency_seconds"]:.4f} |')
    Path(args.summary).write_text('\n'.join(lines)+'\n');Path(args.table).write_text('\n'.join(latex)+'\n')
    if summary['complete']:write_discussion(summary, rows)
    print(f'Analysed {len(rows)} measured records; independent experiment complete={summary["complete"]}.')
if __name__=='__main__':main()
