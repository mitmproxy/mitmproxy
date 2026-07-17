import json, re
from mitmproxy import http

PII_PATTERNS = [
    (r'\b[\w\.-]+@[\w\.-]+\.\w+\b',     'EMAIL'),
    (r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b', 'CARD'),
    (r'\b\+?\d[\d\s\-\.\(\)]{6,}\d\b',  'PHONE'),
    (r'\b[A-Z]{2}\d{6,9}\b',            'DOC_ID'),
]

_pii_store: dict[str, dict[str, str]] = {}

def request(flow: http.HTTPFlow):
    if not any(pat in flow.request.pretty_url for pat in [
        "chat.openai.com/backend-api/conversation",
        "/v1/chat/completions",
    ]):
        return
    try:
        body = json.loads(flow.request.content)
    except json.JSONDecodeError:
        return
    store: dict[str, str] = {}
    modified = False
    for msg in body.get("messages", []):
        content = msg.get("content")
        if not isinstance(content, str):
            continue
        for pattern, label in PII_PATTERNS:
            def replacer(m, lbl=label, s=store):
                p = f'[{lbl}_{len(s):03d}]'
                s[p] = m.group(0)
                return p
            new_c = re.sub(pattern, replacer, content)
            if new_c != content:
                content = new_c
                modified = True
        if modified:
            msg["content"] = content
    if modified:
        flow.request.content = json.dumps(body).encode()
        _pii_store[flow.id] = store
        print(f"[PII] Redacted {len(store)} items in {flow.id}")

def response(flow: http.HTTPFlow):
    store = _pii_store.pop(flow.id, None)
    if not store:
        return
    text = flow.response.get_text()
    for placeholder, original in store.items():
        text = text.replace(placeholder, original)
    flow.response.set_text(text)
