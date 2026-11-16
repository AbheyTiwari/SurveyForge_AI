import pandas as pd
def load_csv(path): return pd.read_csv(path,encoding='utf-8-sig')
def profile(df):
    sensitive=[c for c in df.columns if any(k in c.lower() for k in ('नाम या मोबाइल','मोबाइल नंबर','contact','phone','email','e-mail','ईमेल','name','नाम'))]
    safe=df.drop(columns=sensitive,errors='ignore')
    return {'rows':int(len(df)),'columns':int(len(df.columns)),'sensitive_columns_excluded':sensitive,'missing':safe.isna().sum().to_dict(),
      'duplicates':int(safe.duplicated().sum()),'types':safe.dtypes.astype(str).to_dict(),
      'frequencies':{c:safe[c].value_counts(dropna=False).head(30).to_dict() for c in safe.select_dtypes('object').columns}}

