from pathlib import Path
import csv, json
from .form_parser import parse_form
from .dataset_analyzer import load_csv,profile
from .data_generator import generate
from .normalizer import normalize
from .validator import validate
from .analytics import summarize
from .web_research import SOURCES
def _paths(cfg): return cfg['paths']
def _source(cfg):
    p=_paths(cfg)['original_csv']; return load_csv(p)
def run_generate(cfg,count=None,seed=None):
    paths=_paths(cfg); source=_source(cfg); n=count if count is not None else cfg['generation']['count']; seed=seed if seed is not None else cfg['generation']['seed']
    schema=None; schema_path=Path(paths.get('live_form_schema_json','data/processed/live_form_schema.json'))
    if schema_path.exists():
        schema=json.loads(schema_path.read_text(encoding='utf-8'))
        configured_url=cfg.get('submission',{}).get('form_url','')
        if schema.get('form_url')!=configured_url:
            print('Ignoring inspected form schema because its URL differs from config.yaml; inspect the configured form again.')
            schema=None
    headers=list(source.columns)
    if schema:
        timestamp=[c for c in headers if c.casefold()=='timestamp']
        # Keep an email column from the response export even when Google Forms
        # exposes it as response metadata rather than a normal question card.
        email_columns=[c for c in headers if any(marker in c.casefold() for marker in ('email','e-mail','ईमेल'))]
        questions=[q['title'] for q in schema.get('questions',[]) if q.get('title')]
        question_keys={c.strip().casefold() for c in questions}
        metadata_email=[c for c in email_columns if c.strip().casefold() not in question_keys]
        headers=timestamp+metadata_email+questions
        if metadata_email:
            print(f'Retaining synthetic email column(s): {metadata_email}')
    df=generate(headers,source,n,seed,schema=schema); out=Path(paths['synthetic_csv']); out.parent.mkdir(parents=True,exist_ok=True); df.to_csv(out,index=False,encoding='utf-8-sig'); print(f'Generated {len(df)} synthetic records: {out}')
def run_validate(cfg):
    paths=_paths(cfg); src=_source(cfg); synth=load_csv(paths['synthetic_csv']) if Path(paths['synthetic_csv']).exists() else None
    report={'original':validate(src),'synthetic':validate(synth) if synth is not None else {'valid':None,'note':'No synthetic CSV yet'}}
    out=Path(paths['report_dir']); out.mkdir(parents=True,exist_ok=True); (out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(report,ensure_ascii=False,indent=2))
def run_analyze(cfg):
    paths=_paths(cfg); df=_source(cfg); summarize(df,paths['report_dir']); (Path(paths['report_dir'])/'profile.json').write_text(json.dumps(profile(df),ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (Path(paths['report_dir'])/'research_sources.json').write_text(json.dumps(SOURCES,ensure_ascii=False,indent=2),encoding='utf-8')
def run_all(cfg,count=None,seed=None):
    paths=_paths(cfg)
    if Path(paths['form_pdf']).exists():
        parse_form(paths['form_pdf'],paths['original_csv'],paths['schema_json'])
    elif not Path(paths['schema_json']).exists():
        raise FileNotFoundError(f"Form PDF or prebuilt schema required: {paths['form_pdf']} / {paths['schema_json']}")
    run_generate(cfg,count,seed)
    generated=load_csv(paths['synthetic_csv']); normalized,mappings=normalize(generated)
    Path(paths['normalized_csv']).parent.mkdir(parents=True,exist_ok=True); normalized.to_csv(paths['normalized_csv'],index=False,encoding='utf-8-sig')
    Path(paths['report_dir']).mkdir(parents=True,exist_ok=True); mappings.to_csv(Path(paths['report_dir'])/'normalization_mappings.csv',index=False,encoding='utf-8-sig')
    run_validate(cfg); run_analyze(cfg)

