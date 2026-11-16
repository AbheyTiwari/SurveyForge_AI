from pathlib import Path
import pandas as pd
def _md_table(frame):
    cols=[str(c) for c in frame.columns]; rows=[[str(v) for v in row] for row in frame.values.tolist()]
    return '| '+' | '.join(cols)+' |\n| '+' | '.join(['---']*len(cols))+' |\n'+'\n'.join('| '+' | '.join(r)+' |' for r in rows)
def summarize(df,outdir):
    p=Path(outdir); p.mkdir(parents=True,exist_ok=True)
    df=df.drop(columns=[c for c in df.columns if any(k in c.lower() for k in ('नाम या मोबाइल','मोबाइल नंबर','contact','phone','email','e-mail','ईमेल','name','नाम'))],errors='ignore')
    if df.empty:
        (p/'analysis.md').write_text('# SurveyForge AI analysis\n\nNo source response rows were provided.\n',encoding='utf-8')
        return
    numeric=df.select_dtypes(include='number'); stats=_md_table(numeric.describe().reset_index().rename(columns={'index':'stat'})) if len(numeric.columns) else 'No numeric response columns detected.'
    lines=['# SurveyForge AI analysis','',f'- Rows: {len(df)}',f'- Columns: {len(df.columns)}',f'- Exact duplicate rows: {int(df.duplicated().sum())}','','## Numeric summary','',stats,'','## Category frequencies','']
    for c in df.select_dtypes('object').columns:
        if c in ('surveyforge_id','record_lineage'): continue
        lines += [f'### {c}','',_md_table(df[c].value_counts(dropna=False).head(20).rename_axis(c).reset_index(name='count')),'']
    (p/'analysis.md').write_text('\n'.join(lines),encoding='utf-8')
    try:
        import matplotlib.pyplot as plt
        for c in df.select_dtypes('object').columns[:8]:
            if c in ('surveyforge_id','record_lineage'): continue
            counts=df[c].value_counts().head(12); fig,ax=plt.subplots(figsize=(9,5)); counts.sort_values().plot.barh(ax=ax); ax.set_title(c[:80]); fig.tight_layout(); fig.savefig(p/(f'chart_{len(list(p.glob("chart_*.png"))):02d}.png')); plt.close(fig)
    except ImportError: pass

