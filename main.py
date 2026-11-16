"""SurveyForge AI command line entry point."""
import argparse
from pathlib import Path
import json
from src.pipeline import run_generate, run_validate, run_analyze, run_all
from src.form_filler import dry_run
from src.form_inspector import inspect_form

def main():
    p=argparse.ArgumentParser(description='SurveyForge AI: survey analysis and synthetic data toolkit')
    p.add_argument('--config',default='config.yaml'); sub=p.add_subparsers(dest='command',required=True)
    for name in ('generate','validate','analyze','run','submit','inspect-form'):
        sp=sub.add_parser(name)
        if name=='inspect-form':
            sp.add_argument('--url',help='Google Forms URL; defaults to submission.form_url in config')
        else:
            sp.add_argument('--count',type=int); sp.add_argument('--seed',type=int)
        if name=='submit':
            sp.add_argument('--live',action='store_true',help='Submit records to the configured live form')
            sp.add_argument('--dry-run',action='store_true',help='Show the prepared CSV without submitting')
            sp.add_argument('--start-index',type=int,default=0,help='Skip this many leading CSV rows when resuming a partial live run')
    a=p.parse_args(); cfg=json.loads(Path(a.config).read_text(encoding='utf-8'))
    if a.command=='inspect-form': inspect_form(cfg,a.url)
    elif a.command=='generate': run_generate(cfg,a.count,a.seed)
    elif a.command=='validate': run_validate(cfg)
    elif a.command=='analyze': run_analyze(cfg)
    elif a.command=='run': run_all(cfg,a.count,a.seed)
    else:
        if a.count is not None: run_generate(cfg,a.count,a.seed)
        dry_run(cfg,live=a.live,start_index=a.start_index)
if __name__=='__main__': main()

