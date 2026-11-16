"""Build a portable schema from the form PDF and its response export headers."""
import csv, json, re
from pathlib import Path
from pypdf import PdfReader

def parse_form(pdf_path,csv_path,out_path):
    reader=PdfReader(str(pdf_path)); text='\n'.join(p.extract_text() or '' for p in reader.pages)
    with open(csv_path,encoding='utf-8-sig',newline='') as f: headers=next(csv.reader(f))
    questions=[]
    for i,h in enumerate(headers[1:],1):
        q={'id':f'q{i:02d}','title':h,'required':i<30,'type':'text','options':[]}
        if re.search(r'क्या|कौन|इस्तेमाल कर सकते|जुड़ना चाहेंगे|दोबारा संपर्क',h): q['type']='choice'
        if re.search(r'कितनी|कितना|कमाई|मजदूरी|खर्च|कमीशन|फीस|जल्दी|आयु|साल',h): q['type']='text_or_numeric_range'
        if i==30: q.update(required=False,sensitive=True,exclude_from_synthetic=True)
        questions.append(q)
    schema={'title':'टेक्नीशियन सर्वे — घरेलू मरम्मत सेवाएँ','language':'hi','source_pdf':Path(pdf_path).name,
      'page_count':len(reader.pages),'description':'PDF text was cross-checked with response export headers. Google Forms PDF export does not expose all validation/branching settings.',
      'pdf_text_chars':len(text),'questions':questions}
    Path(out_path).parent.mkdir(parents=True,exist_ok=True); Path(out_path).write_text(json.dumps(schema,ensure_ascii=False,indent=2),encoding='utf-8')
    return schema

