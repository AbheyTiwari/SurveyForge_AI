import pandas as pd
def validate(df, required=None):
    issues=[]; required=required or []
    for c in required:
        if c not in df: issues.append({'type':'missing_column','column':c})
        else:
            for idx in df.index[df[c].isna() | (df[c].astype(str).str.strip()=='')]: issues.append({'type':'required_empty','row':int(idx),'column':c})
    if 'surveyforge_id' in df and df.surveyforge_id.duplicated().any(): issues.append({'type':'duplicate_id','count':int(df.surveyforge_id.duplicated().sum())})
    dup=int(df.drop(columns=['surveyforge_id','synthetic_seed'],errors='ignore').duplicated().sum())
    if dup: issues.append({'type':'duplicate_record','count':dup})
    return {'valid':not issues,'row_count':len(df),'issue_count':len(issues),'issues':issues}

