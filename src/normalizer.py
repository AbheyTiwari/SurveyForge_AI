import re, pandas as pd
def normalize(df):
    out=df.copy(); mapping=[]
    for c in out.select_dtypes('object').columns:
        if c in ('record_lineage','surveyforge_id'): continue
        for value in out[c].dropna().unique():
            v=str(value); new=re.sub(r'\s+',' ',v).strip()
            if new!=v: mapping.append({'column':c,'original':v,'normalized':new})
        out[c]=out[c].map(lambda x: re.sub(r'\s+',' ',x).strip() if isinstance(x,str) else x)
    return out,pd.DataFrame(mapping,columns=['column','original','normalized'])

