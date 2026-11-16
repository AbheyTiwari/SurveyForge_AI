"""Schema-driven synthetic generator. Every row is labeled synthetic."""
import random, uuid, re, unicodedata
import pandas as pd

# Synthetic contact labels for the optional final form question. These are
# generated demo identities, not names sourced from survey respondents.
INDIAN_MALE_NAMES = [
 'Aarav','Vivaan','Aditya','Arjun','Sai','Reyansh','Ayaan','Krishna','Ishaan','Shaurya',
 'Atharv','Advait','Dhruv','Kabir','Rohan','Rahul','Aman','Ankit','Ansh','Dev',
 'Harsh','Karan','Kartik','Lakshya','Manav','Mohit','Nikhil','Pranav','Raj','Rajat',
 'Rishi','Rohit','Sachin','Sagar','Sameer','Samarth','Sanjay','Shrey','Siddharth','Suraj',
 'Varun','Vikram','Yash','Abhishek','Akash','Amit','Anand','Arnav','Ashwin','Bharat',
 'Chirag','Deepak','Gaurav','Hitesh','Jay','Kunal','Madhav','Manish','Mayank','Naveen',
 'Neeraj','Om','Piyush','Prateek','Raghav','Rajesh','Rakesh','Ramesh','Sandeep','Shashank',
 'Shubham','Tarun','Uday','Vinay','Vikas','Vishal','Ajay','Amar','Anurag','Arvind',
 'Bhavesh','Chetan','Dinesh','Girish','Govind','Hemant','Jatin','Jeevan','Lalit','Mahesh',
 'Mukesh','Naresh','Nitin','Pankaj','Prakash','Rituraj','Shankar','Tanmay','Yuvraj','Manoj',
]
CONTACT_PREFIXES = ('81','91','98','87')
PHONE_FIELD_LABELS = ('मोबाइल नंबर','फोन नंबर','mobile number','phone number','contact number','telephone number')
EMAIL_FIELD_LABELS = ('email','e-mail','ईमेल')
EMAIL_WORDS = ('homefix','service','connect','repair','works','local','pro','care','team','help')

def _is_email_field(column):
    label=str(column).casefold()
    return any(marker in label for marker in EMAIL_FIELD_LABELS)

def _is_phone_field(column):
    label=re.sub(r'^\s*\d+[.)]?\s*','',str(column)).strip().casefold()
    return any(marker in label for marker in PHONE_FIELD_LABELS) or bool(re.match(r'^(phone|mobile|telephone)\b',label))

def _is_combined_identity_field(column):
    label=str(column).casefold()
    return any(marker in label for marker in ('नाम या मोबाइल','name or mobile','name or phone','name/mobile'))

def _is_name_field(column):
    label=re.sub(r'^\s*\d+[.)]?\s*','',str(column)).strip().casefold()
    return ('नाम लिखें' in label or 'अपना नाम' in label or 'पूरा नाम' in label
            or label in {'name','full name','your name','name (optional)','respondent name'}
            or label.startswith(('what is your name','what is your full name','please enter your name')))

def _question_key(value):
    value=re.sub(r'^\s*\d+[.)]?\s*','',str(value))
    return ''.join(ch for ch in unicodedata.normalize('NFC',value).casefold()
                   if unicodedata.category(ch)[0] in 'LMN')

def _synthetic_email(index, name, rng):
    local=name.casefold()
    style=index % 5
    if style==1: local=f'{local}.{rng.choice(EMAIL_WORDS)}'
    elif style==2: local=f'{local}{rng.randrange(100,9999)}'
    elif style==3: local=f'{local}_{rng.choice(EMAIL_WORDS)}'
    elif style==4: local=f'{local}.{rng.choice(EMAIL_WORDS)}{rng.randrange(10,99)}'
    if index>=len(INDIAN_MALE_NAMES): local=f'{local}{index+1}'
    return f'{local}@example.com'

DEMO_CHOICES={
 1:['प्लंबर','इलेक्ट्रीशियन','बढ़ई (कारपेंटर)','पेंटर'],
 2:['1 साल से कम','1–3 साल','4–7 साल','8–15 साल','15 साल से अधिक'],
 3:['फरीदाबाद','दिल्ली','गुरुग्राम','नोएडा','दिल्ली-एनसीआर के अलग-अलग इलाकों में'],
 4:['अकेले','दोस्तों या दूसरे कारीगरों के साथ','अपनी दुकान है'],
 5:['हाँ, सभी जरूरी औजार हैं','कुछ औजार हैं'],
 6:['पुराने ग्राहक','ग्राहकों की सिफारिश से','WhatsApp या सोशल मीडिया से'],
 7:['हाँ, लगभग हमेशा','अधिकतर मिल जाता है','कभी मिलता है, कभी नहीं'],
 8:['1 काम','2–3 काम','4–5 काम'],
 9:['नए ग्राहक नहीं मिलते','बहुत ज्यादा प्रतिस्पर्धा है','कोई खास परेशानी नहीं'],
 10:['अक्सर','कभी-कभी','बहुत कम','कभी नहीं'],
 11:['₹10,000–₹20,000','₹20,001–₹30,000','₹30,001–₹50,000'],
 12:['₹501–₹1,000','₹1,000 से अधिक','काम के हिसाब से बहुत बदलता है'],
 13:['₹50 से कम','₹50–₹100','₹101–₹200'],
 14:['काम पूरा होते ही','अक्सर उसी दिन','कुछ दिन बाद'],
 15:['हाँ','अभी तय नहीं है','नहीं'],
 16:['ज्यादा ग्राहक मिलना','समय पर भुगतान','अपने इलाके में काम मिलना'],
 17:['ज्यादा कमीशन देना','भुगतान में देरी','कोई चिंता नहीं'],
 18:['हाँ, आसानी से','थोड़ी मदद से'],
 19:['अपने घर के पास','अपने शहर में कहीं भी','पास के शहरों में भी'],
 20:['कोई कमीशन नहीं','हर काम पर 5%','हर काम पर 10%'],
 21:['ग्राहक मुझे सीधे पैसे दे','प्लेटफॉर्म पैसे लेकर मुझे दे','दोनों में से कोई भी'],
 22:['नहीं','छोटी एक बार की फीस','केवल तभी भुगतान करूँगा/करूँगी जब काम मिलेगा'],
 23:['30–60 मिनट','1–2 घंटे','अपने काम और दूरी के हिसाब से'],
 24:['हाँ, अक्सर','कभी-कभी','बहुत कम','कभी नहीं'],
 25:['ऐप के जरिए ही काम करना पसंद करूँगा/करूँगी','सीधे काम करूँगा/करूँगी'],
 26:['भरोसे के कारण','अच्छे काम के कारण','समय पर पहुँचने के कारण'],
 27:['ज्यादा ग्राहक','समय पर भुगतान','ग्राहकों का भरोसा'],
 28:['ऐप को आसान बनाइए','ज्यादा ग्राहक जोड़िए','समय पर भुगतान कराइए'],
 29:['हाँ','नहीं'],
}

def _demo_answer(column,rng):
    import re
    match=re.match(r'\s*(\d+)\.',str(column))
    number=int(match.group(1)) if match else None
    choices=DEMO_CHOICES.get(number)
    return rng.choice(choices) if choices else ''

def _schema_default(question):
    if not question.get('required',False):
        return ''
    if question.get('type') in ('radio','checkbox','dropdown','unsupported'):
        raise ValueError(f"Cannot generate a valid required choice for {question.get('title','unknown question')!r}: no enabled options were discovered. Re-inspect the form.")
    input_type=question.get('input_type',question.get('type','text')).casefold()
    if input_type=='number': return '1'
    if input_type=='email': return 'demo@example.com'
    if input_type=='url': return 'https://example.com'
    if input_type=='date': return '2026-01-01'
    if input_type=='time': return '12:00'
    title=question.get('title','')
    if any('\u0900' <= ch <= '\u097f' for ch in title):
        return 'डेमो के लिए कृत्रिम उत्तर'
    return 'Synthetic demo response'

def generate(headers, source, count, seed=42, grok=None, schema=None):
    if count<0 or count>100000: raise ValueError('count must be between 0 and 100000')
    rng=random.Random(seed); name_rng=random.Random(seed ^ 0x5F0A7E); rows=[]
    names=name_rng.sample(INDIAN_MALE_NAMES,len(INDIAN_MALE_NAMES))
    schema_by_title={_question_key(q.get('title','')):q for q in (schema or {}).get('questions',[])}
    for index in range(count):
        row={}
        for col in headers:
            if col.lower()=='timestamp': row[col]=f'2026-01-{rng.randint(1,28):02d} {rng.randint(8,19):02d}:{rng.randint(0,59):02d}:00'
            elif _is_email_field(col):
                row[col]=_synthetic_email(index,names[index % len(names)],name_rng)
            elif _is_combined_identity_field(col):
                name=names[index % len(names)]
                number=f'{name_rng.choice(CONTACT_PREFIXES)}{name_rng.randrange(100_000_000):08d}'
                row[col]=f'{name}, {number}'
            elif _is_phone_field(col):
                row[col]=f'{name_rng.choice(CONTACT_PREFIXES)}{name_rng.randrange(100_000_000):08d}'
            elif _is_name_field(col):
                row[col]=names[index % len(names)]
            else:
                vals=source[col].dropna().astype(str).tolist() if col in source else []
                vals=[x for x in vals if x.strip()]
                question=schema_by_title.get(_question_key(col),{})
                options=question.get('options',[])
                if options and question.get('type') in ('radio','dropdown'):
                    valid={_question_key(option) for option in options}
                    vals=[value for value in vals if _question_key(value) in valid]
                elif options and question.get('type')=='checkbox':
                    valid={_question_key(option):option for option in options}
                    filtered=[]
                    for value in vals:
                        parts=[part.strip() for part in re.split(r'[,;]',value) if part.strip()]
                        accepted=[valid[_question_key(part)] for part in parts if _question_key(part) in valid]
                        if accepted: filtered.append(', '.join(accepted))
                    vals=filtered
                if vals:
                    row[col]=rng.choice(vals)
                elif options:
                    if question.get('type')=='checkbox':
                        row[col]=', '.join(rng.sample(options,k=rng.randint(1,len(options))))
                    else:
                        row[col]=rng.choice(options)
                elif question:
                    row[col]=_schema_default(question)
                else:
                    row[col]=_demo_answer(col,rng)
        rows.append(row)
    df=pd.DataFrame(rows,columns=headers)
    df.insert(0,'surveyforge_id',[str(uuid.uuid4()) for _ in range(count)])
    df['record_lineage']='synthetic'; df['synthetic_seed']=seed
    return df

