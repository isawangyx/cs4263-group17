#!/usr/bin/env python3
"""Rebuild local artifacts without generating pilot fixtures or spending model allowance."""
import argparse,shutil,subprocess
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--compile-report',action='store_true');args=p.parse_args()
    if args.compile_report and not Path('report.tex').exists():
        p.error('Report sources remain local and are not included in the code-only repository.')
    if args.compile_report and not shutil.which('tectonic'):
        p.error('Install Tectonic on PATH to compile the local report source.')
    commands=[['python3','generate_benchmark.py'],['python3','check_benchmark.py'],['python3','export_llm_inputs.py'],['python3','csp_solver.py'],['python3','validator.py','--inputs','classical_outputs.jsonl','--output','classical_scores.jsonl'],['python3','-m','unittest','-v','test_project.py']]
    if Path('experiments/v2_llm_outputs.jsonl').exists():
        commands += [['python3','validator.py','--inputs','experiments/v2_llm_outputs.jsonl','--output','experiments/v2_llm_scores.jsonl']]
    commands += [['python3','analyze_results.py']]
    for cmd in commands:print('+',' '.join(cmd),flush=True);subprocess.run(cmd,check=True)
    if args.compile_report:
        compiler=shutil.which('tectonic')
        subprocess.run([compiler,'report.tex','--keep-logs','--outdir','submission'],check=True)
    print('Local rebuild complete. Existing independent trial records preserved. Model calls require an explicit llm_runner.py command.')
if __name__=='__main__':main()
