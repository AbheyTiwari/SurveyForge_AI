"""Inspect a Google Form's visible question structure without submitting it."""
import json
import re
import unicodedata
from pathlib import Path


def normalize_form_url(form_url):
    """Normalize a pasted responder link and discard copied trailing junk."""
    value=''.join(ch for ch in str(form_url) if unicodedata.category(ch) not in ('Cf','Cc') and ch!='\ufffd').strip()
    short=re.match(r'^https://forms\.gle/([A-Za-z0-9_-]+)',value,re.I)
    if short:
        return f'https://forms.gle/{short.group(1)}'
    long=re.match(r'^https://docs\.google\.com/forms/(?:u/\d+/)?d/(e/)?([A-Za-z0-9_-]+)/(?:viewform|formResponse)(?:[/?#]|$)',value,re.I)
    if long:
        prefix='e/' if long.group(1) else ''
        return f'https://docs.google.com/forms/d/{prefix}{long.group(2)}/viewform'
    raise ValueError('Enter a Google Forms responder link, such as https://forms.gle/FORM_ID. Remove any extra text before the link.')


def _visible_text(locator):
    try:
        if locator.count():
            return locator.first.inner_text().strip()
    except Exception:
        pass
    return ''


def _question_title(item):
    for selector in ('[role="heading"]', '.M7eMe'):
        title = _visible_text(item.locator(selector))
        if title:
            return title
    text = item.inner_text().strip()
    return next((line.strip() for line in text.splitlines() if line.strip()), '')


def _labels(locator):
    labels = []
    for i in range(locator.count()):
        option = locator.nth(i)
        if option.get_attribute('aria-disabled') == 'true':
            continue
        label = (option.get_attribute('aria-label') or option.inner_text()).strip()
        if label and label.casefold().strip(': ') not in {'other','अन्य'} and label not in labels:
            labels.append(label)
    return labels


def _disabled_labels(locator):
    labels = []
    for i in range(locator.count()):
        option = locator.nth(i)
        if option.get_attribute('aria-disabled') == 'true':
            label = (option.get_attribute('aria-label') or option.inner_text()).strip()
            if label:
                labels.append(label)
    return labels


def _inspect_page(page):
    found = []
    items = page.locator('[role="listitem"]')
    for i in range(items.count()):
        item = items.nth(i)
        if not item.is_visible():
            continue
        title = _question_title(item)
        if not title:
            continue
        radios = item.locator('[role="radio"]')
        checks = item.locator('[role="checkbox"]')
        dropdown = item.locator('[role="listbox"]')
        fields = item.locator('textarea, input[type="text"], input[type="number"], input[type="email"], input[type="date"], [role="textbox"]')
        disabled_options = []
        if radios.count():
            kind, options = 'radio', _labels(radios)
            disabled_options = _disabled_labels(radios)
        elif checks.count():
            kind, options = 'checkbox', _labels(checks)
            disabled_options = _disabled_labels(checks)
        elif dropdown.count():
            dropdown.first.click()
            option_items = page.locator('[role="option"]')
            options = _labels(option_items)
            disabled_options = _disabled_labels(option_items)
            page.keyboard.press('Escape')
            kind = 'dropdown'
        elif fields.count():
            input_types = [fields.nth(j).get_attribute('type') or 'text' for j in range(fields.count())]
            kind, options = 'text', []
        else:
            kind, options = 'unsupported', []
        required = item.get_attribute('aria-required') == 'true' or item.locator('[aria-required="true"]').count() > 0
        question = {'title': title, 'type': kind, 'required': required, 'options': options}
        if disabled_options:
            question['disabled_options'] = disabled_options
        if kind == 'text' and fields.count():
            question['input_type'] = input_types[0]
        found.append(question)
    return found


def _answer_for_inspection(page):
    """Use temporary in-browser values only to navigate sections; never submit."""
    items = page.locator('[role="listitem"]')
    for i in range(items.count()):
        item = items.nth(i)
        if not item.is_visible():
            continue
        radios = item.locator('[role="radio"]')
        checks = item.locator('[role="checkbox"]')
        dropdown = item.locator('[role="listbox"]')
        if radios.count():
            for j in range(radios.count()):
                option=radios.nth(j)
                if option.get_attribute('aria-disabled') != 'true' and option.is_enabled():
                    option.click()
                    break
        elif checks.count():
            for j in range(checks.count()):
                option=checks.nth(j)
                if option.get_attribute('aria-disabled') != 'true' and option.is_enabled():
                    option.click()
                    break
        elif dropdown.count():
            dropdown.first.click()
            options = page.locator('[role="option"]')
            if options.count():
                options.first.click()
        else:
            fields = item.locator('textarea, input[type="text"], input[type="number"], input[type="email"], input[type="date"], [role="textbox"]')
            for j in range(fields.count()):
                field = fields.nth(j)
                if field.is_visible():
                    try:
                        current = field.input_value()
                    except Exception:
                        current = field.get_attribute('value') or ''
                    if not current:
                        field_type = (field.get_attribute('type') or 'text').casefold()
                        sample = {'number': '1', 'email': 'test@example.com', 'date': '2026-01-01',
                                  'time': '12:00', 'month': '2026-01', 'url': 'https://example.com'}.get(field_type, 'Inspection sample')
                        if field_type != 'file':
                            field.fill(sample)


def inspect_form(cfg, form_url=None):
    settings = cfg.get('submission', {})
    form_url = normalize_form_url(form_url or settings.get('form_url', ''))
    paths = cfg.get('paths', {})
    output = Path(paths.get('live_form_schema_json', 'data/processed/live_form_schema.json'))
    questions, seen = [], set()
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(form_url, wait_until='domcontentloaded', timeout=45000)
            try:
                page.locator('[role="listitem"]').first.wait_for(state='visible', timeout=15000)
            except PlaywrightTimeoutError as exc:
                title=page.title()
                body=page.locator('body').inner_text()[:300]
                raise RuntimeError(f'No Google Forms questions appeared for {form_url!r} (page title: {title!r}, page text: {body!r}). Check that this is a public responder link and that the form accepts responses.') from exc
            page.wait_for_timeout(1000)  # Let Google Forms finish rendering controls and option states.
            for _ in range(100):
                body = page.locator('body').inner_text()
                if 'captcha' in body.casefold():
                    raise RuntimeError('CAPTCHA or anti-abuse prompt encountered; inspection stopped.')
                for question in _inspect_page(page):
                    key = re.sub(r'\s+', ' ', question['title']).casefold()
                    if key not in seen:
                        questions.append(question)
                        seen.add(key)
                blocked = [q for q in questions if q.get('required')
                           and q.get('type') in ('radio', 'checkbox', 'dropdown', 'unsupported')
                           and not q.get('options')]
                if blocked:
                    details = '; '.join(
                        f"{q['title']} (disabled: {', '.join(q.get('disabled_options', [])) or 'none detected'})"
                        for q in blocked
                    )
                    raise RuntimeError(f'Could not inspect enabled choices for required question(s): {details}. No responses were submitted.')
                next_button = page.get_by_role('button', name=re.compile(r'^(next|अगला)$', re.I))
                if not next_button.count():
                    break  # In particular, never click Submit.
                _answer_for_inspection(page)
                next_button.first.click()
                page.wait_for_timeout(350)
            else:
                raise RuntimeError('Form inspection exceeded 100 sections; stopping before Submit.')
        finally:
            browser.close()
    if not questions:
        raise RuntimeError('No form questions were found. The form may require sign-in or use unsupported controls.')
    schema = {'form_url': form_url, 'question_count': len(questions), 'questions': questions,
              'note': 'Inspected question labels and visible controls. Temporary answers were used only to navigate pages; Submit was never clicked.'}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Inspected {len(questions)} questions; schema saved to {output}. No response was submitted.')
    return schema

