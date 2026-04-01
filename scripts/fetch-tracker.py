#!/usr/bin/env python3
"""
Fetch posts from Yandex Tracker BLOG queue and convert to Hugo markdown.
"""

import os
import re
import json
import time
import hashlib
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────
TRACKER_API    = "https://api.tracker.yandex.net/v2"
OAUTH_TOKEN    = os.environ["TRACKER_TOKEN"]
ORG_ID         = os.environ["TRACKER_ORG_ID"]
SITE_URL       = os.environ.get("SITE_URL", "https://tarmolov.ru")
_SCRIPT_DIR    = Path(__file__).parent
CONTENT_DIR    = Path(os.environ.get("CONTENT_DIR", _SCRIPT_DIR / "content/posts"))
STATE_FILE     = Path(os.environ.get("STATE_FILE", _SCRIPT_DIR / ".tracker-state.json"))

FIELD_PREFIX   = "635bb3a32bf1dd5fdb87553e--"
FIELD_SITE_URL = f"{FIELD_PREFIX}siteUrl"
FIELD_PROD     = f"{FIELD_PREFIX}production"
FIELD_PUBDATE  = f"{FIELD_PREFIX}publishDateTime"

BLOG_ISSUE_RE  = re.compile(r'https://tracker\.yandex\.ru/(BLOG-\d+)')

# Tracker attachment URLs: /ajax/v2/attachments/<id> or full tracker.yandex.ru paths
ATTACHMENT_RE  = re.compile(
    r'!\[([^\]]*)\]\((/ajax/v2/attachments/\d+[^\)]*|https://tracker\.yandex\.ru/[^\)]*attachments/\d+[^\)]*)\)'
)
# External images
EXT_IMAGE_RE   = re.compile(
    r'!\[([^\]]*)\]\((https?://[^\)]+\.(png|jpg|jpeg|gif|webp)(?:\?[^\)]*)?)\)',
    re.IGNORECASE
)
# External videos
EXT_VIDEO_RE   = re.compile(
    r'\[([^\]]*)\]\((https?://[^\)]+\.(mp4|mov|webm|avi)(?:\?[^\)]*)?)\)',
    re.IGNORECASE
)

# ── HTTP helpers ────────────────────────────────────────────────────────────
def api_get(path, params=None):
    url = f"{TRACKER_API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Authorization": f"OAuth {OAUTH_TOKEN}",
        "X-Org-ID": ORG_ID,
    })
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def api_post(path, data):
    import urllib.error
    body = json.dumps(data).encode()
    req = urllib.request.Request(f"{TRACKER_API}{path}", data=body, method="POST", headers={
        "Authorization": f"OAuth {OAUTH_TOKEN}",
        "X-Org-ID": ORG_ID,
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} on POST {path}: {e.read().decode(errors='replace')}")
        raise

def api_patch(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(f"{TRACKER_API}{path}", data=body, method="PATCH", headers={
        "Authorization": f"OAuth {OAUTH_TOKEN}",
        "X-Org-ID": ORG_ID,
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def download_bytes(url, auth=False):
    """Download raw bytes from URL, optionally with Tracker auth."""
    headers = {"User-Agent": "Mozilla/5.0"}
    if auth:
        headers["Authorization"] = f"OAuth {OAUTH_TOKEN}"
        headers["X-Org-ID"] = ORG_ID
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read(), dict(r.headers)

# ── Tracker helpers ─────────────────────────────────────────────────────────
def search_issues(daily=False):
    if daily:
        query = 'Queue: BLOG Resolution: Fixed Blog."время публикации": today() "Sort by": Blog."время публикации" ASC'
    else:
        query = 'Queue: BLOG Resolution: Fixed "Sort by": Blog."время публикации" ASC'
    issues, page = [], 1
    while True:
        batch = api_post(f"/issues/_search?perPage=50&page={page}", {"query": query})
        if not batch:
            break
        issues.extend(batch)
        if len(batch) < 50:
            break
        page += 1
    return issues

def get_issue_attachments(key):
    """Return list of attachment dicts for an issue."""
    try:
        return api_get(f"/issues/{key}/attachments")
    except Exception:
        return []

# ── Slug & path helpers ─────────────────────────────────────────────────────
_TRANSLIT = {
    'а': 'a',  'б': 'b',  'в': 'v',  'г': 'g',  'д': 'd',
    'е': 'e',  'ё': 'yo', 'ж': 'zh', 'з': 'z',  'и': 'i',
    'й': 'y',  'к': 'k',  'л': 'l',  'м': 'm',  'н': 'n',
    'о': 'o',  'п': 'p',  'р': 'r',  'с': 's',  'т': 't',
    'у': 'u',  'ф': 'f',  'х': 'kh', 'ц': 'ts', 'ч': 'ch',
    'ш': 'sh', 'щ': 'sch','ъ': '',   'ы': 'y',  'ь': '',
    'э': 'e',  'ю': 'yu', 'я': 'ya',
}

def transliterate(text):
    return "".join(_TRANSLIT.get(ch.lower(), ch) for ch in text)

def slugify(text):
    text = transliterate(text).lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    return text or "post"

def issue_slug(issue):
    # key is e.g. "BLOG-3" → id = "3"
    key = issue.get("key", "")
    issue_id = key.split("-")[-1] if "-" in key else key
    return f"{issue_id}-{slugify(issue['summary'])}"[:60].rstrip('-')

def issue_site_url(issue):
    return f"{SITE_URL}/posts/{issue_slug(issue)}/"

# ── Media helpers ───────────────────────────────────────────────────────────
def fname_from_url(url):
    """Extract filename from URL."""
    fname = url.split("?")[0].split("/")[-1]
    if not fname or '.' not in fname:
        fname = hashlib.md5(url.encode()).hexdigest()[:12]
    return fname

def download_to(url, dest, auth=False):
    """Download URL to dest path. Returns True on success."""
    if dest.exists():
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  Downloading → {dest.name}")
    try:
        data, _ = download_bytes(url, auth=auth)
        dest.write_bytes(data)
        return True
    except Exception as e:
        print(f"  WARN: failed {url}: {e}")
        return False

def is_video(fname):
    return Path(fname).suffix.lower() in {'.mp4', '.mov', '.webm', '.avi'}

def _feature_name(fname, counter):
    """First image becomes feature.{ext} for Blowfish card support."""
    if counter[0] == 0:
        return f"feature{Path(fname).suffix.lower()}"
    return fname

def make_summary(text, max_chars=200):
    """Extract plain-text summary from markdown: first non-empty paragraph, stripped of markup."""
    for para in re.split(r'\n{2,}', text):
        line = para.strip()
        if not line:
            continue
        # strip markdown: images, links, bold/italic, headings, shortcodes
        line = re.sub(r'!\[[^\]]*\]\([^\)]*\)', '', line)
        line = re.sub(r'\[[^\]]*\]\([^\)]*\)', lambda m: m.group(0).split('](')[0][1:], line)
        line = re.sub(r'\{\{<[^>]*>\}\}.*?\{\{</[^>]*>\}\}', '', line, flags=re.DOTALL)
        line = re.sub(r'[*_`#>]', '', line)
        line = ' '.join(line.split())
        if line:
            return line[:max_chars].rstrip() + ('…' if len(line) > max_chars else '')
    return ""

# ── Build slug→siteUrl map for cross-linking ────────────────────────────────
def build_site_url_map(issues):
    m = {}
    for issue in issues:
        m[issue["key"]] = issue.get(FIELD_SITE_URL) or issue_site_url(issue)
    return m

def resolve_site_url(key, site_url_map):
    """Return siteUrl for a BLOG key, fetching from Tracker if not in map."""
    if key in site_url_map:
        return site_url_map[key]
    try:
        issue = api_get(f"/issues/{key}")
        url = issue.get(FIELD_SITE_URL) or issue_site_url(issue)
        site_url_map[key] = url  # cache for future calls
        return url
    except Exception as e:
        print(f"  WARN: could not resolve siteUrl for {key}: {e}")
        return None

# ── Description processing ──────────────────────────────────────────────────
def process_description(description, issue_key, site_url_map, post_dir, attachments_by_id):
    if not description:
        return ""
    text = description
    image_counter = [0]  # mutable counter shared across replace functions

    # 1. Replace BLOG issue links with siteUrl
    def replace_blog_link(m):
        key = m.group(1)
        url = resolve_site_url(key, site_url_map)
        return url if url else m.group(0)
    text = BLOG_ISSUE_RE.sub(replace_blog_link, text)

    # 2. Replace Tracker attachment images (inline attachments)
    def replace_attachment(m):
        alt = m.group(1)
        raw_url = m.group(2)

        # Try to find attachment filename from the alt text or attachments list
        # Tracker inline syntax: ![filename.jpg](/ajax/v2/attachments/123?inline=true =400x)
        # Extract just the path without size hint
        url_part = raw_url.split(" ")[0]  # remove " =400x" etc

        # Build full URL if relative
        if url_part.startswith("/"):
            full_url = f"https://tracker.yandex.ru{url_part}"
        else:
            full_url = url_part

        # Try to find the real filename from attachments list
        # Extract attachment ID from URL
        att_id_m = re.search(r'/attachments/(\d+)', url_part)
        att_id = att_id_m.group(1) if att_id_m else None

        # Use attachment metadata for filename and download URL
        if att_id and att_id in attachments_by_id:
            att = attachments_by_id[att_id]
            fname = att["name"] or fname_from_url(url_part)
            download_url = att["content_url"] or full_url
        elif alt and '.' in alt:
            fname = alt
            download_url = full_url
        else:
            fname = fname_from_url(url_part)
            download_url = full_url

        if not is_video(fname):
            fname = _feature_name(fname, image_counter)
            image_counter[0] += 1
        dest = post_dir / fname
        rel = fname

        if download_to(download_url, dest, auth=True):
            return f"![{alt}]({rel})"
        return m.group(0)

    text = ATTACHMENT_RE.sub(replace_attachment, text)

    # 3. Replace external images
    def replace_ext_image(m):
        alt, url = m.group(1), m.group(2)
        fname = fname_from_url(url)
        fname = _feature_name(fname, image_counter)
        image_counter[0] += 1
        dest = post_dir / fname
        if download_to(url, dest):
            return f"![{alt}]({fname})"
        return m.group(0)
    text = EXT_IMAGE_RE.sub(replace_ext_image, text)

    # 4. Replace external videos
    def replace_ext_video(m):
        label, url = m.group(1), m.group(2)
        fname = fname_from_url(url)
        dest = post_dir / fname
        if download_to(url, dest):
            return f"[{label}]({fname})"
        return m.group(0)
    text = EXT_VIDEO_RE.sub(replace_ext_video, text)

    return text

# ── Issue → markdown ────────────────────────────────────────────────────────
def issue_to_markdown(issue, site_url_map, post_dir):
    key = issue["key"]
    title = issue["summary"]
    description = issue.get("description", "")
    components = [c["display"] for c in issue.get("components", [])]
    production_url = issue.get(FIELD_PROD, "")
    pub_date_raw = issue.get(FIELD_PUBDATE) or issue.get("createdAt", "")

    try:
        date_str = datetime.fromisoformat(
            pub_date_raw.replace("Z", "+00:00")
        ).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    except Exception:
        date_str = pub_date_raw

    # Build attachment id→info map  {id: {name, content_url}}
    attachments = get_issue_attachments(key)
    attachments_by_id = {
        str(a.get("id", "")): {"name": a.get("name", ""), "content_url": a.get("content", "")}
        for a in attachments
    }

    # If the first attachment is a video, download it unconditionally
    if attachments:
        first = attachments[0]
        fname = first.get("name", "")
        if is_video(fname):
            download_to(first.get("content", ""), post_dir / fname, auth=True)

    body = process_description(description, key, site_url_map, post_dir, attachments_by_id)
    summary = make_summary(body)

    if production_url:
        tg_callout = (
            f'{{{{< alert icon="brands/telegram" >}}}}\n'
            f'Оригинал опубликован в [Telegram]({production_url})\n'
            f'{{{{< /alert >}}}}\n\n'
        )
        body = tg_callout + body

    fm = ["---", f'title: "{title.replace(chr(34), chr(39))}"', f"date: {date_str}",
          f"slug: {issue_slug(issue)}"]
    if summary:
        fm.append(f'summary: "{summary.replace(chr(34), chr(39))}"')
    if components:
        fm.append("tags:")
        for c in components:
            fm.append(f"  - {c}")
    if production_url:
        fm.append(f'telegram: "{production_url}"')
    fm.append(f'tracker: "{key}"')
    fm.append("---")

    return "\n".join(fm) + "\n\n" + body

# ── State ───────────────────────────────────────────────────────────────────
def load_state():
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))

# ── Main ────────────────────────────────────────────────────────────────────
def main():
    state = load_state()
    first_run = not state.get("last_run")
    print(f"Mode: {'full sync' if first_run else 'daily sync'}")

    issues = search_issues() if first_run else search_issues(daily=True)
    print(f"Found {len(issues)} issues")

    if not issues:
        print("Nothing to do.")
        return

    site_url_map = build_site_url_map(issues)
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)

    for issue in issues:
        key = issue["key"]
        slug = issue_slug(issue)
        post_dir = CONTENT_DIR / slug
        post_dir.mkdir(parents=True, exist_ok=True)

        if (post_dir / "index.md").exists():
            print(f"Skipping {key}: already synced")
            continue

        print(f"Processing {key}: {issue['summary'][:60]}")

        post_dir.mkdir(parents=True, exist_ok=True)
        md = issue_to_markdown(issue, site_url_map, post_dir)
        (post_dir / "index.md").write_text(md, encoding="utf-8")

        url = issue_site_url(issue)
        if issue.get(FIELD_SITE_URL) != url:
            api_patch(f"/issues/{key}", {FIELD_SITE_URL: url})
            print(f"  ✓ siteUrl → {url}")

        time.sleep(0.1)

    state["last_run"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    print("Done.")

def patch_urls():
    """Patch siteUrl in Tracker for all existing posts without re-downloading."""
    index_files = sorted(CONTENT_DIR.glob("*/index.md"))
    print(f"Found {len(index_files)} posts, patching siteUrl...")
    for idx in index_files:
        text = idx.read_text(encoding="utf-8")
        m = re.search(r'^tracker:\s+"?(BLOG-\d+)"?', text, re.MULTILINE)
        slug_m = re.search(r'^slug:\s+(\S+)', text, re.MULTILINE)
        if not m or not slug_m:
            continue
        key = m.group(1)
        slug = slug_m.group(1)
        url = f"{SITE_URL}/posts/{slug}/"
        try:
            issue = api_get(f"/issues/{key}")
            if issue.get(FIELD_SITE_URL) == url:
                print(f"  – {key}: already set")
                continue
            api_patch(f"/issues/{key}", {FIELD_SITE_URL: url})
            print(f"  ✓ {key} → {url}")
        except Exception as e:
            print(f"  ✗ {key}: {e}")
        time.sleep(0.1)
    print("Done.")

def replace_tg_links():
    """Build telegram→siteUrl map from Tracker and replace links in all posts."""
    print("Fetching all issues from Tracker...")
    issues = search_issues()
    tg_map = {}
    for issue in issues:
        tg = issue.get(FIELD_PROD, "")
        site = issue.get(FIELD_SITE_URL, "")
        if tg and site:
            tg_map[tg.rstrip("/")] = site.rstrip("/") + "/"
    print(f"Built map: {len(tg_map)} telegram → siteUrl pairs")

    alert_re = re.compile(r'{{< alert[^>]*>}}.*?{{< /alert >}}', re.DOTALL)

    index_files = sorted(CONTENT_DIR.glob("*/index.md"))
    changed = 0
    for idx in index_files:
        text = idx.read_text(encoding="utf-8")

        # Mask frontmatter and alert blocks so we don't touch them
        fm_re = re.compile(r'\A---\n.*?\n---\n', re.DOTALL)
        fm_match = fm_re.match(text)
        frontmatter = fm_match.group(0) if fm_match else ""
        body = text[len(frontmatter):]

        alerts = alert_re.findall(body)
        placeholder = "\x00ALERT{}\x00"
        masked = alert_re.sub(lambda m, i=iter(range(len(alerts))): placeholder.format(next(i)), body)

        new_masked = masked
        for tg_url, site_url in tg_map.items():
            new_masked = new_masked.replace(tg_url, site_url)

        # Restore alert blocks and prepend frontmatter
        for i, block in enumerate(alerts):
            new_masked = new_masked.replace(placeholder.format(i), block)
        new_text = frontmatter + new_masked

        if new_text != text:
            idx.write_text(new_text, encoding="utf-8")
            print(f"  ✓ {idx.parent.name}")
            changed += 1
    print(f"Done. Updated {changed} files.")

if __name__ == "__main__":
    import sys
    if "--patch-urls" in sys.argv:
        patch_urls()
    elif "--replace-tg-links" in sys.argv:
        replace_tg_links()
    else:
        main()
