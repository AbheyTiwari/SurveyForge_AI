import re
import pandas as pd
from src.data_generator import INDIAN_MALE_NAMES, generate
from src.normalizer import normalize
from src.validator import validate
def test_generation_count_lineage_and_synthetic_contacts():
    cols=['Timestamp','काम','यदि हाँ, तो अपना नाम या मोबाइल नंबर लिखें (वैकल्पिक)']
    source=pd.DataFrame({'Timestamp':['2026-01-01'],'काम':['इलेक्ट्रीशियन'],cols[-1]:['DEMO-CONTACT-DO-NOT-CALL']})
    result=generate(cols,source,100,seed=7)
    assert len(result)==100 and result.surveyforge_id.is_unique
    assert set(result.record_lineage)=={'synthetic'}
    contacts=result[cols[-1]].tolist()
    names=[value.split(', ',1)[0] for value in contacts]
    numbers=[value.split(', ',1)[1] for value in contacts]
    assert len(INDIAN_MALE_NAMES)==100 and len(set(INDIAN_MALE_NAMES))==100
    assert len(set(names))==100 and 'DEMO-CONTACT-DO-NOT-CALL' not in contacts
    assert all(re.fullmatch(r'(81|91|98|87)\d{8}',number) for number in numbers)
def test_normalize_and_validate():
    df=pd.DataFrame({'surveyforge_id':['a'],'required':[' x  y ']})
    clean,mappings=normalize(df)
    assert clean.required.iloc[0]=='x y' and len(mappings)==1
    assert validate(clean,['required'])['valid']

