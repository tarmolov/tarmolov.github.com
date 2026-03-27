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
CONTENT_DIR    = Path(os.environ.get("CONTENT_DIR", "content/posts"))
STATE_FILE     = Path(os.environ.get("STATE_FILE", ".tracker-state.json"))

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
    body = json.dumps(data).encode()
    req = urllib.request.Request(f"{TRACKER_API}{path}", data=body, method="POST", headers={
        "Authorization": f"OAuth {OAUTH_TOKEN}",
        "X-Org-ID": ORG_ID,
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

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
def search_issues(extra_filter=None):
    f = {"queue": "BLOG", "resolution": "notEmpty()"}
    if extra_filter:
        f.update(extra_filter)
    issues, page = [], 1
    while True:
        batch = api_post(f"/issues/_search?perPage=50&page={page}", {"filter": f})
        if not batch:
            break
        issues.extend(batch)
        if len(batch) < 50:
            break
        page += 1
    def pub_key(i):
        return i.get(FIELD_PUBDATE) or i.get("createdAt") or ""
    return sorted(issues, key=pub_key)

def get_issue_attachments(key):
    """Return list of attachment dicts for an issue."""
    try:
        return api_get(f"/issues/{key}/attachments")
    except Exception:
        return []

# ── Slug & path helpers ─────────────────────────────────────────────────────
def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    return text or "post"

def issue_slug(issue):
    return slugify(issue["summary"])[:60].rstrip('-')

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

# ── Build slug→siteUrl map for cross-linking ────────────────────────────────
def build_site_url_map(issues):
    m = {}
    for issue in issues:
        m[issue["key"]] = issue.get(FIELD_SITE_URL) or issue_site_url(issue)
    return m

# ── Description processing ──────────────────────────────────────────────────
def process_description(description, issue_key, site_url_map, post_dir, attachments_by_name):
    if not description:
        return ""
    text = description

    # 1. Replace BLOG issue links with siteUrl
    def replace_blog_link(m):
        key = m.group(1)
        return site_url_map.get(key, m.group(0))
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

        dest_subdir = "videos" if is_video(fname) else "images"
        dest = post_dir / dest_subdir / fname

        if download_to(download_url, dest, auth=True):
            return f"![{alt}]({dest_subdir}/{fname})"
        return m.group(0)

    text = ATTACHMENT_RE.sub(replace_attachment, text)

    # 3. Replace external images
    def replace_ext_image(m):
        alt, url = m.group(1), m.group(2)
        fname = fname_from_url(url)
        dest = post_dir / "images" / fname
        if download_to(url, dest):
            return f"![{alt}](images/{fname})"
        return m.group(0)
    text = EXT_IMAGE_RE.sub(replace_ext_image, text)

    # 4. Replace external videos
    def replace_ext_video(m):
        label, url = m.group(1), m.group(2)
        fname = fname_from_url(url)
        dest = post_dir / "videos" / fname
        if download_to(url, dest):
            return f"[{label}](videos/{fname})"
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

    body = process_description(description, key, site_url_map, post_dir, attachments_by_id)

    fm = ["---", f'title: "{title.replace(chr(34), chr(39))}"', f"date: {date_str}",
          f"slug: {issue_slug(issue)}"]
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
    print(f"Mode: {'full sync' if first_run else 'incremental (last month)'}")

    issues = search_issues() if first_run else search_issues({"updated": "month()"})
    print(f"Found {len(issues)} issues")

    site_url_map = build_site_url_map(issues)
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)

    for issue in issues:
        key = issue["key"]
        slug = issue_slug(issue)
        post_dir = CONTENT_DIR / slug
        post_dir.mkdir(parents=True, exist_ok=True)

        print(f"Processing {key}: {issue['summary'][:60]}")

        md = issue_to_markdown(issue, site_url_map, post_dir)
        (post_dir / "index.md").write_text(md, encoding="utf-8")

        # TODO: write siteUrl back to Tracker (disabled during debugging)
        # url = issue_site_url(issue)
        # if issue.get(FIELD_SITE_URL) != url:
        #     api_patch(f"/issues/{key}", {FIELD_SITE_URL: url})
        #     print(f"  ✓ siteUrl → {url}")

        time.sleep(0.1)

    state["last_run"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    print("Done.")

if __name__ == "__main__":
    main()
