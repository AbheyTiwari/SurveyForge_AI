"""Google Forms Playwright adapter with explicit per-run live-submit opt-in."""
import json, re, time
import unicodedata
from pathlib import Path
import pandas as pd

def _norm(value):
    text=unicodedata.normalize('NFC',re.sub(r'^\s*\d+[.)]?\s*','',str(value)))
    text=text.replace('\u093c','')
    return ''.join(ch for ch in text if unicodedata.category(ch)[0] in 'LMN').casefold()

def _answer_item(page, item, question, answer):
    if isinstance(answer,(list,tuple,set)):
        answer_parts=[str(value).strip() for value in answer if str(value).strip()]
        answer=', '.join(answer_parts)
    else:
        answer=str(answer).strip()
    if not answer: return False
    radios=item.locator('[role="radio"]')
    if radios.count():
        disabled_matches=[]
        for i in range(radios.count()):
            option=radios.nth(i); label=_norm(option.get_attribute('aria-label') or option.inner_text())
            if label==_norm(answer):
                disabled_matches.append(option)
                if option.get_attribute('aria-disabled')=='true' or not option.is_enabled():
                    continue
                option.click(); return True
        if disabled_matches:
            deadline=time.monotonic()+3.0
            while time.monotonic()<deadline:
                for option in disabled_matches:
                    if option.get_attribute('aria-disabled')!='true' and option.is_enabled():
                        option.click(); return True
                page.wait_for_timeout(200)
            raise ValueError(f'Form option remained disabled for {question!r}: {answer!r}. Re-inspect the form and regenerate.')
        raise ValueError(f"No radio option matched {question!r}: {answer!r}")
    checks=item.locator('[role="checkbox"]')
    if checks.count():
        # CSV cells may encode multi-select answers as comma/pipe-delimited text,
        # or occasionally as a Python-style list string.
        raw=re.sub(r"^[\[({]|[\])}]$",'',answer)
        wanted=[part.strip().strip("\"'") for part in re.split(r'[,|;]',raw) if part.strip().strip("\"'")]
        matched=[]; available=[]
        for i in range(checks.count()):
            option=checks.nth(i)
            label=option.get_attribute('aria-label') or option.inner_text()
            normalized=_norm(label)
            if normalized: available.append(label.strip())
            requested=next((part for part in wanted if _norm(part)==normalized),None)
            if requested is None: continue
            if option.get_attribute('aria-disabled')=='true' or not option.is_enabled():
                raise ValueError(f'Checkbox option is disabled for {question!r}: {requested!r}.')
            if option.get_attribute('aria-checked')!='true':
                option.click()
                # Wait for Google Forms JS to update aria-checked (up to 2 s).
                deadline=time.monotonic()+2.0
                while option.get_attribute('aria-checked')!='true' and time.monotonic()<deadline:
                    page.wait_for_timeout(100)
            if option.get_attribute('aria-checked')!='true':
                # Fall back to the keyboard interaction supported by ARIA checkboxes.
                option.focus()
                option.press('Space')
                deadline=time.monotonic()+2.0
                while option.get_attribute('aria-checked')!='true' and time.monotonic()<deadline:
                    page.wait_for_timeout(100)
            if option.get_attribute('aria-checked')!='true':
                disabled_ancestor=option.locator('xpath=ancestor-or-self::*[@aria-disabled="true" or @disabled][1]')
                disabled_info='none detected'
                if disabled_ancestor.count():
                    disabled_info=(disabled_ancestor.first.get_attribute('aria-label')
                                   or disabled_ancestor.first.get_attribute('class')
                                   or 'disabled ancestor')
                classes=option.get_attribute('class') or ''
                raise RuntimeError(f'Checkbox option did not become selected for {question!r}: {requested!r}; aria-checked={option.get_attribute("aria-checked")!r}, aria-disabled={option.get_attribute("aria-disabled")!r}, enabled={option.is_enabled()}, class={classes!r}, disabled_ancestor={disabled_info!r}.')
            matched.append(requested)
        missing=[part for part in wanted if not any(_norm(part)==_norm(value) for value in matched)]
        if missing:
            raise ValueError(f'Checkbox options did not all match for {question!r}; unmatched: {missing!r}; available: {available!r}.')
        return bool(matched)
    dropdown=item.locator('[role="listbox"]')
    if dropdown.count():
        dropdown.first.click()
        options=page.locator('[role="option"]')
        for i in range(options.count()):
            option=options.nth(i)
            if _norm(option.inner_text())==_norm(answer):
                if option.get_attribute('aria-disabled')=='true' or not option.is_enabled():
                    continue
                option.click(); return True
        raise ValueError(f"No dropdown option matched {question!r}: {answer!r}")
    fields=item.locator('textarea, input:not([type="hidden"]):not([type="radio"]):not([type="checkbox"]):not([type="submit"]):not([type="file"]), [role="textbox"]')
    if fields.count(): fields.first.fill(answer); return True
    return False

def _visible_page_signature(page):
    items=page.locator('[role="listitem"]'); visible=[]
    for i in range(items.count()):
        item=items.nth(i)
        if item.is_visible():
            visible.append(re.sub(r'\s+',' ',item.inner_text()).strip())
    return tuple(visible)

def _visible_question_titles(page):
    items=page.locator('[role="listitem"]'); titles=[]
    for i in range(items.count()):
        item=items.nth(i)
        if item.is_visible():
            text=item.inner_text().strip()
            if text:
                titles.append(text.splitlines()[0].strip())
    return titles

def _item_title(item):
    for selector in ('[role="heading"]', '.M7eMe'):
        title=item.locator(selector)
        if title.count():
            value=title.first.inner_text().strip()
            if value: return value
    text=item.inner_text().strip()
    return next((line.strip() for line in text.splitlines() if line.strip()), '')

def _validation_blockers(page):
    blockers=[]; items=page.locator('[role="listitem"]')
    for i in range(items.count()):
        item=items.nth(i)
        if not item.is_visible(): continue
        controls=item.locator('[role="radio"], [role="checkbox"], [role="listbox"], textarea, input:not([type="hidden"]):not([type="submit"]):not([type="radio"]):not([type="checkbox"]):not([type="file"]), [role="textbox"]')
        if not controls.count(): continue
        title=_item_title(item)
        invalid=item.get_attribute('aria-invalid')=='true' or item.locator('[aria-invalid="true"]').count()>0
        required=item.get_attribute('aria-required')=='true' or item.locator('[aria-required="true"]').count()>0
        if invalid:
            blockers.append(title); continue
        if not required: continue
        radios=item.locator('[role="radio"]'); checks=item.locator('[role="checkbox"]')
        if radios.count() and not any(radios.nth(j).get_attribute('aria-checked')=='true' for j in range(radios.count())):
            blockers.append(title)
        elif checks.count() and not any(checks.nth(j).get_attribute('aria-checked')=='true' for j in range(checks.count())):
            blockers.append(title)
        elif not radios.count() and not checks.count():
            fields=item.locator('textarea, input:not([type="hidden"]):not([type="submit"]):not([type="radio"]):not([type="checkbox"]):not([type="file"]), [role="textbox"]')
            if fields.count():
                try: empty=not fields.first.input_value().strip()
                except Exception: empty=not (fields.first.get_attribute('value') or '').strip()
                if empty: blockers.append(title)
    # Google Forms often renders its validation message in the question card
    # without setting aria-invalid/aria-required on the card or control.
    for selector in ('[role="alert"]','[aria-live="assertive"]'):
        messages=page.locator(selector)
        for i in range(messages.count()):
            message=messages.nth(i)
            if not message.is_visible(): continue
            value=message.inner_text().strip().casefold()
            if not any(marker in value for marker in ('required','आवश्यक')): continue
            card=message.locator('xpath=ancestor::*[@role="listitem"][1]')
            if card.count():
                title=_item_title(card.first)
                if title: blockers.append(title)
    return list(dict.fromkeys(x for x in blockers if x))

def _control_kind(item):
    if item.locator('[role="radio"]').count(): return 'radio'
    if item.locator('[role="checkbox"]').count(): return 'checkbox'
    if item.locator('[role="listbox"]').count(): return 'dropdown'
    if item.locator('textarea, input:not([type="hidden"]):not([type="submit"]):not([type="radio"]):not([type="checkbox"]):not([type="file"]), [role="textbox"]').count(): return 'text'
    return 'unknown'

def _fill_record(page, row, headers):
    completed=set();
    max_sections=max(100,len(headers)+1)
    email_columns=[c for c in headers if any(marker in c.casefold() for marker in ('email','e-mail','ईमेल'))]
    for page_number in range(1,max_sections+1):
        # Google Forms may render collected email as a form-level input rather
        # than as a normal role=listitem question card.
        email_fields=page.locator('input[type="email"]:visible')
        for column in email_columns:
            if column in completed or not str(row.get(column,'')).strip(): continue
            target=next((email_fields.nth(i) for i in range(email_fields.count())
                         if email_fields.nth(i).is_visible()),None)
            if target is not None:
                target.fill(str(row[column]))
                completed.add(column)
                print(f'[form] page={page_number} question={column!r} control=email result=filled')
        items=page.locator('[role="listitem"]'); current=[]
        for i in range(items.count()):
            item=items.nth(i)
            if not item.is_visible(): continue
            text=_norm(_item_title(item))
            for column in headers:
                if column.lower()=='timestamp' or column in completed: continue
                title=_norm(column)
                # Match only the card's question heading, never a coincidental option label.
                if title and title==text:
                    current.append((column,item)); break
        mapped=[column for column,_ in current]
        print(f'[form] page={page_number} visible_items={sum(1 for i in range(items.count()) if items.nth(i).is_visible())} matched_questions={len(mapped)}')
        for column,item in current:
            answer=row.get(column,'')
            if str(answer).strip():
                kind=_control_kind(item)
                try:
                    if not _answer_item(page,item,column,answer):
                        raise RuntimeError(f'Unsupported question control: {column}')
                except Exception as exc:
                    print(f'[form] page={page_number} question={column!r} control={kind} result=ERROR error={type(exc).__name__}: {exc}')
                    raise
                print(f'[form] page={page_number} question={column!r} control={kind} result=answered')
            else:
                print(f'[form] page={page_number} question={column!r} control={_control_kind(item)} result=blank_in_generated_row')
            completed.add(column)
        submit=page.get_by_role('button',name=re.compile(r'^(submit|जमा करें|भेजें)$',re.I))
        if submit.count():
            missing_email=[c for c in email_columns if str(row.get(c,'')).strip() and c not in completed]
            if missing_email:
                raise RuntimeError(f'Cannot submit synthetic email field(s) {missing_email!r}: the responder page exposed no editable email input. If Email Address is Google-collected metadata, this public form flow cannot assign a synthetic address; add a visible email question or change the form collection setting.')
            # Wait for Google's formResponse POST, not localized confirmation copy.
            with page.expect_response(
                lambda response: 'formresponse' in response.url.casefold()
                and response.request.method.upper() == 'POST',
                timeout=20000,
            ) as response_info:
                submit.first.click()
            response=response_info.value
            if response.status >= 400:
                raise RuntimeError(f'Google Forms rejected the response (HTTP {response.status}).')
            return response.status
        next_button=page.get_by_role('button',name=re.compile(r'^(next|अगला)$',re.I))
        if next_button.count():
            button=next_button.first
            if not button.is_enabled():
                raise RuntimeError(f'Google Forms disabled Next at questions: {_visible_question_titles(page)}')
            before=_visible_page_signature(page)
            button.click(); page.wait_for_timeout(800)
            if _visible_page_signature(page)==before:
                alerts=[]
                for selector in ('[role="alert"]','[aria-live="assertive"]'):
                    alerts.extend(page.locator(selector).all_inner_texts())
                detail='; '.join(x.strip() for x in alerts if x.strip())
                blockers=_validation_blockers(page)
                raise RuntimeError(f'Google Forms did not advance after Next on page {page_number}. Unanswered/invalid required questions: {blockers or "Google did not expose a specific question"}. Matched questions on this page: {mapped}. Visible questions: {_visible_question_titles(page)}. Form messages: {detail or "none shown"}.')
            continue
        # Some single-page forms have a submit button whose accessible name has extra text.
        buttons=page.get_by_role('button')
        names=[buttons.nth(i).inner_text().strip() for i in range(buttons.count())]
        raise RuntimeError(f'Could not find Next/Submit control; visible buttons: {names}')
    raise RuntimeError(f'Form exceeded {max_sections} sections or required questions did not become reachable.')

def _submit(cfg, live, start_index=0):
    paths=cfg['paths']; settings=cfg.get('submission',{})
    csv_path=Path(paths['synthetic_csv']); form_url=settings.get('form_url','')
    if not live:
        print(f'DRY RUN: {csv_path} is ready from row {start_index}; no form opened and no response submitted.')
        return
    if not settings.get('allow_live_submission'):
        raise RuntimeError('Live submissions are disabled in config.yaml.')
    if not form_url.startswith('https://docs.google.com/forms/') and not form_url.startswith('https://forms.gle/'):
        raise ValueError('Configure a Google Forms HTTPS URL before submitting.')
    if not csv_path.exists(): raise FileNotFoundError(f'Generate records first: {csv_path}')
    df=pd.read_csv(csv_path,encoding='utf-8-sig').fillna('')
    total_rows=len(df)
    if start_index<0 or start_index>len(df):
        raise ValueError(f'start_index must be between 0 and {len(df)}.')
    if start_index:
        print(f'Resuming at row {start_index+1}; skipping {start_index} previously attempted row(s).')
        df=df.iloc[start_index:].copy()
    if 'record_lineage' not in df or not (df.record_lineage=='synthetic').all():
        raise ValueError('Refusing submission: every row must be explicitly marked synthetic.')
    if len(df)>100:
        raise ValueError('Live submission is limited to 100 records per run; split larger batches deliberately.')
    delay=max(1.0,min(60.0,float(settings.get('delay_seconds',2))))
    log=Path(paths.get('report_dir','reports'))/'form_submissions.jsonl'; log.parent.mkdir(parents=True,exist_ok=True)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        try:
            page=browser.new_page()
            for source_index,record in df.iterrows():
                row_number=int(source_index)+1
                record_id=record.get('surveyforge_id','unknown')
                print(f'[submit] row={row_number}/{total_rows} id={record_id} opening_form')
                try:
                    page.goto(form_url,wait_until='domcontentloaded',timeout=45000)
                    page.locator('[role="listitem"]').first.wait_for(state='visible',timeout=15000)
                    page.wait_for_timeout(1000)
                    if 'captcha' in page.locator('body').inner_text().casefold():
                        raise RuntimeError('CAPTCHA or anti-abuse prompt encountered; stopping without bypass.')
                    status=_fill_record(page,record.to_dict(),list(df.columns))
                except Exception as exc:
                    print(f'[submit] row={row_number} id={record_id} result=FAILED confirmation=not_received error={type(exc).__name__}: {exc}')
                    raise
                with log.open('a',encoding='utf-8') as stream:
                    stream.write(json.dumps({'surveyforge_id':record.get('surveyforge_id'),'status':'form_response_received','http_status':status},ensure_ascii=False)+'\n')
                print(f'[submit] row={row_number} id={record_id} result=CONFIRMED http_status={status}')
                time.sleep(delay)
        finally: browser.close()

def dry_run(cfg,live=False,start_index=0):
    _submit(cfg,live,start_index)

