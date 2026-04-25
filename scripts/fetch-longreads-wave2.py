#!/usr/bin/env python3
import json
import os
import re
import shutil
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from PIL import Image

TRACKER_API = 'https://api.tracker.yandex.net/v2'
SITE_URL = 'https://tarmolov.ru'
SECRETS = json.load(open('/home/openclaw/.openclaw/secrets.json'))['yandex']
OAUTH_TOKEN = SECRETS['trackerOauthToken']
ORG_ID = str(SECRETS['trackerOrgId'])
REPO = Path('/home/openclaw/.openclaw/workspace/openclaw/tarmolov.github.com')
CONTENT_DIR = REPO / 'content/posts'
FIELD_PREFIX = '69d5312edd54410ee987bc97--'
FIELD_SITE_URL = f'{FIELD_PREFIX}siteUrl'
FIELD_PROD = f'{FIELD_PREFIX}production'
FIELD_PUBDATE = f'{FIELD_PREFIX}publishDateTime'
ISSUES = ['LONGREAD-1', 'LONGREAD-2', 'LONGREAD-3', 'LONGREAD-4', 'LONGREAD-6', 'LONGREAD-7', 'LONGREAD-8', 'LONGREAD-9']
TRACKER_LINK_RE = re.compile(r'https://tracker\.yandex\.ru/(LONGREAD-\d+)')
ATT_RE = re.compile(r'!\[([^\]]*)\]\((/ajax/v2/attachments/\d+[^\)]*|https://tracker\.yandex\.ru/[^\)]*attachments/\d+[^\)]*)\)')
EXT_IMG_RE = re.compile(r'!\[([^\]]*)\]\((https?://[^\)]+\.(png|jpg|jpeg|gif|webp)(?:\?[^\)]*)?)\)', re.I)
TRAN = {'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo','ж':'zh','з':'z','и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'kh','ц':'ts','ч':'ch','ш':'sh','щ':'sch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya'}


def translit(s: str) -> str:
    return ''.join(TRAN.get(ch.lower(), ch) for ch in s)


def slugify(s: str) -> str:
    s = translit(s).lower().strip()
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'[\s_]+', '-', s)
    s = re.sub(r'-+', '-', s).strip('-')
    return s or 'post'


def issue_slug(issue: dict) -> str:
    n = issue['key'].split('-')[-1]
    return f"{n}-{slugify(issue['summary'])}"[:60].rstrip('-')


def issue_url(issue: dict) -> str:
    return f"{SITE_URL}/posts/{issue_slug(issue)}/"


def api_get(path: str):
    req = urllib.request.Request(
        TRACKER_API + path,
        headers={'Authorization': f'OAuth {OAUTH_TOKEN}', 'X-Org-ID': ORG_ID},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def api_patch(path: str, data: dict):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        TRACKER_API + path,
        data=body,
        method='PATCH',
        headers={
            'Authorization': f'OAuth {OAUTH_TOKEN}',
            'X-Org-ID': ORG_ID,
            'Content-Type': 'application/json',
        },
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def download(url: str, auth: bool = False):
    headers = {'User-Agent': 'Mozilla/5.0'}
    if auth:
        headers['Authorization'] = f'OAuth {OAUTH_TOKEN}'
        headers['X-Org-ID'] = ORG_ID
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read(), dict(r.headers)


def attachments(key: str):
    try:
        return api_get(f'/issues/{key}/attachments')
    except Exception:
        return []


def webp_convert(raw_path: Path, dest: Path):
    img = Image.open(raw_path)
    if img.mode in ('P', 'LA'):
        img = img.convert('RGBA')
    elif img.mode not in ('RGB', 'RGBA'):
        img = img.convert('RGB')
    w, h = img.size
    img.save(dest, 'WEBP', quality=85, method=6)
    return w, h


def save_image(url: str, dest_base: Path, auth: bool = False):
    last_exc = None
    for candidate in [url]:
        try:
            data, _ = download(candidate, auth=auth)
            tmp = dest_base.with_suffix('.bin')
            tmp.write_bytes(data)
            out = dest_base.with_suffix('.webp')
            w, h = webp_convert(tmp, out)
            tmp.unlink(missing_ok=True)
            return out.name, w, h
        except Exception as e:
            last_exc = e
    raise last_exc


def make_summary(text: str, max_chars: int = 200) -> str:
    for para in re.split(r'\n{2,}', text):
        line = para.strip()
        if not line:
            continue
        line = re.sub(r'\{\{<[^>]*>\}\}', '', line)
        line = re.sub(r'!\[[^\]]*\]\([^\)]*\)', '', line)
        line = re.sub(r'\[([^\]]*)\]\([^\)]*\)', r'\1', line)
        line = re.sub(r'[*_`#>]', '', line)
        line = ' '.join(line.split())
        if line:
            return line[:max_chars].rstrip() + ('…' if len(line) > max_chars else '')
    return ''


def process(issue: dict, site_map: dict):
    key = issue['key']
    post_dir = CONTENT_DIR / issue_slug(issue)
    if post_dir.exists():
        shutil.rmtree(post_dir)
    post_dir.mkdir(parents=True)

    atts = attachments(key)
    by_id = {str(a.get('id')): a for a in atts}
    counter = 0
    body = issue.get('description') or ''

    def repl_lr(m):
        k = m.group(1)
        return site_map.get(k, m.group(0))

    body_local = TRACKER_LINK_RE.sub(repl_lr, body)

    def repl_att(m):
        nonlocal counter
        alt, url = m.group(1), m.group(2)
        size_m = re.search(r'=\s*(\d+)x(\d+)\s*$', url)
        req_w = req_h = None
        if size_m:
            req_w, req_h = size_m.group(1), size_m.group(2)
        url_part = url.split(' ')[0]
        full = url_part if url_part.startswith('http') else 'https://tracker.yandex.ru' + url_part
        att_id_m = re.search(r'/attachments/(\d+)', url_part)
        att = by_id.get(att_id_m.group(1)) if att_id_m else None
        base = 'feature' if counter == 0 else str(300 + counter)
        counter += 1
        candidates = []
        if att:
            if att.get('content'):
                candidates.append((att['content'], True))
            if att.get('thumbnail'):
                candidates.append((att['thumbnail'], True))
            if att.get('self'):
                candidates.append((att['self'].rstrip('/') + '/' + urllib.parse.quote(att.get('name') or 'file'), True))
        candidates.append((full, True))
        last = None
        for candidate, need_auth in candidates:
            try:
                name, w, h = save_image(candidate, post_dir / base, auth=need_auth)
                return f'{{{{< postimg src="{name}" width="{req_w or w}" height="{req_h or h}" alt="{alt}" >}}}}'
            except Exception as e:
                last = e
        print(f'WARN: failed to download attachment in {key}: {url} :: {last}')
        return f'![{alt}]({full})'

    body_local = ATT_RE.sub(repl_att, body_local)

    def repl_ext(m):
        nonlocal counter
        alt, url = m.group(1), m.group(2)
        base = 'feature' if counter == 0 else str(300 + counter)
        counter += 1
        name, w, h = save_image(url, post_dir / base, auth=False)
        return f'{{{{< postimg src="{name}" width="{w}" height="{h}" alt="{alt}" >}}}}'

    body_local = EXT_IMG_RE.sub(repl_ext, body_local)

    prod = issue.get(FIELD_PROD, '')
    if prod:
        body_local = '{{< alert icon="brands/telegram" >}}\nОригинал опубликован в [Telegram](' + prod + ')\n{{< /alert >}}\n\n' + body_local

    summary = make_summary(body_local)
    pub = issue.get(FIELD_PUBDATE) or issue.get('createdAt')
    try:
        dt = datetime.fromisoformat(pub.replace('Z', '+00:00')).strftime('%Y-%m-%dT%H:%M:%S+00:00')
    except Exception:
        dt = pub

    fm = [
        '---',
        f'title: "{issue["summary"].replace(chr(34), chr(39)).strip()}"',
        f'date: {dt}',
        f'slug: {issue_slug(issue)}',
    ]
    if summary:
        fm.append(f'summary: "{summary.replace(chr(34), chr(39))}"')
    if prod:
        fm.append(f'telegram: "{prod}"')
    fm.append(f'tracker: "{key}"')
    fm.append('---')
    fm.append('')

    (post_dir / 'index.md').write_text('\n'.join(fm) + body_local + '\n', encoding='utf-8')

    url = issue_url(issue)
    if issue.get(FIELD_SITE_URL) != url:
        api_patch(f'/issues/{key}', {FIELD_SITE_URL: url})
    return key, url


def main():
    issues = [api_get(f'/issues/{k}') for k in ISSUES]
    site_map = {i['key']: issue_url(i) for i in issues}
    result = []
    for issue in issues:
        result.append(process(issue, site_map))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
