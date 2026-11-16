"""Optional xAI Grok client with retries; rule-based fallback remains available."""
import os, time, random, json
class GrokClient:
    def __init__(self):
        self.key=os.getenv('XAI_API_KEY'); self.model=os.getenv('XAI_MODEL','grok-2-latest')
    def complete_json(self, system, prompt, attempts=4):
        if not self.key: return None
        try:
            from openai import OpenAI
            client=OpenAI(api_key=self.key,base_url='https://api.x.ai/v1',timeout=45)
            for i in range(attempts):
                try:
                    r=client.chat.completions.create(model=self.model,temperature=0,
                        response_format={'type':'json_object'},messages=[{'role':'system','content':system},{'role':'user','content':prompt}])
                    return json.loads(r.choices[0].message.content)
                except Exception:
                    if i+1==attempts: raise
                    time.sleep(min(30,2**i+random.random()))
        except Exception as e:
            print(f'Grok unavailable; using rule-based fallback ({type(e).__name__}).')
        return None

