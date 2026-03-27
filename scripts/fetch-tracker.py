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
STATIC_DIR     = Path(os.environ.get("STATIC_DIR", "static"))
STATE_FILE     = Path(os.environ.get("STATE_FILE", ".tracker-state.json"))

FIELD_PREFIX   = "635bb3a32bf1dd5fdb87553e--"
FIELD_SITE_URL = f"{FIELD_PREFIX}siteUrl"
FIELD_PROD     = f"{FIELD_PREFIX}production"
FIELD_PUBDATE  = f"{FIELD_PREFIX}publishDateTime"

BLOG_ISSUE_RE  = re.compile(r'https://tracker\.yandex\.ru/(BLOG-\d+)')
IMAGE_RE       = re.compile(r'!\[([^\]]*)\]\((https?://[^\)]+\.(png|jpg|jpeg|gif|webp))\)', re.IGNORECASE)
VIDEO_RE       = re.compile(r'\[(.*?)\]\((https?://[^\)]+\.(mp4|mov|webm|avi))\)', re.IGNORECASE)

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

# ── Tracker helpers ─────────────────────────────────────────────────────────
def search_issues(extra_filter=None):
    """Fetch all matching issues with pagination."""
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
    # Sort by publishDateTime ASC
    def pub_key(i):
        return i.get(FIELD_PUBDATE) or i.get("createdAt") or ""
    return sorted(issues, key=pub_key)

def get_issue(key):
    return api_get(f"/issues/{key}")

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
    slug = issue_slug(issue)
    return f"{SITE_URL}/posts/{slug}/"

# ── Media download ──────────────────────────────────────────────────────────
def download_file(url, dest_dir):
    """Download file, return local path relative to static root."""
    fname = url.split("?")[0].split("/")[-1]
    if not fname or '.' not in fname:
        ext = url.split(".")[-1].split("?")[0][:5]
        fname = hashlib.md5(url.encode()).hexdigest()[:12] + f".{ext}"
    dest = dest_dir / fname
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        print(f"  Downloading {url} → {dest}")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as f:
                f.write(r.read())
        except Exception as e:
            print(f"  WARN: failed to download {url}: {e}")
            return None
    return dest

# ── Build slug→siteUrl map for cross-linking ────────────────────────────────
def build_site_url_map(issues):
    """key → siteUrl"""
    m = {}
    for issue in issues:
        existing = issue.get(FIELD_SITE_URL)
        m[issue["key"]] = existing or issue_site_url(issue)
    return m

# ── Markdown conversion ─────────────────────────────────────────────────────
def process_description(description, issue_key, site_url_map, media_dir):
    if not description:
        return ""
    text = description

    # Replace links to other BLOG issues with siteUrl
    def replace_blog_link(m):
        key = m.group(1)
        if key in site_url_map:
            return site_url_map[key]
        return m.group(0)
    text = BLOG_ISSUE_RE.sub(replace_blog_link, text)

    # Download images and replace URLs
    def replace_image(m):
        alt, url, _ = m.group(1), m.group(2), m.group(3)
        local = download_file(url, media_dir)
        if local:
            rel = "/" + str(local.relative_to(STATIC_DIR))
            return f"![{alt}]({rel})"
        return m.group(0)
    text = IMAGE_RE.sub(replace_image, text)

    # Download videos and replace URLs
    def replace_video(m):
        label, url, _ = m.group(1), m.group(2), m.group(3)
        local = download_file(url, media_dir)
        if local:
            rel = "/" + str(local.relative_to(STATIC_DIR))
            return f"[{label}]({rel})"
        return m.group(0)
    text = VIDEO_RE.sub(replace_video, text)

    return text

def issue_to_markdown(issue, site_url_map):
    key = issue["key"]
    slug = issue_slug(issue)
    title = issue["summary"]
    description = issue.get("description", "")
    components = [c["display"] for c in issue.get("components", [])]
    production_url = issue.get(FIELD_PROD, "")
    pub_date_raw = issue.get(FIELD_PUBDATE) or issue.get("createdAt", "")

    # Parse date
    try:
        pub_date = datetime.fromisoformat(pub_date_raw.replace("Z", "+00:00")).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        date_str = pub_date
    except Exception:
        date_str = pub_date_raw

    # Media dir: static/i/<slug>/
    media_dir = STATIC_DIR / "i" / slug

    # Process description
    body = process_description(description, key, site_url_map, media_dir)

    # Front matter
    fm_lines = [
        "---",
        f'title: "{title.replace(chr(34), chr(39))}"',
        f"date: {date_str}",
        f"slug: {slug}",
    ]
    if components:
        fm_lines.append("tags:")
        for c in components:
            fm_lines.append(f"  - {c}")
    if production_url:
        fm_lines.append(f'telegram: "{production_url}"')
    fm_lines.append(f"tracker: \"{key}\"")
    fm_lines.append("---")

    return "\n".join(fm_lines) + "\n\n" + body

# ── State ───────────────────────────────────────────────────────────────────
def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))

# ── Main ────────────────────────────────────────────────────────────────────
def main():
    state = load_state()
    first_run = not state.get("last_run")

    print(f"Mode: {'full sync' if first_run else 'incremental (last month)'}")

    if first_run:
        issues = search_issues()
    else:
        issues = search_issues({"updated": "month()"})

    print(f"Found {len(issues)} issues")

    site_url_map = build_site_url_map(issues)
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)

    for issue in issues:
        key = issue["key"]
        slug = issue_slug(issue)
        post_dir = CONTENT_DIR / slug
        post_dir.mkdir(parents=True, exist_ok=True)
        post_file = post_dir / "index.md"

        print(f"Processing {key}: {issue['summary'][:60]}")

        md = issue_to_markdown(issue, site_url_map)
        post_file.write_text(md, encoding="utf-8")

        # Write siteUrl back to Tracker
        url = issue_site_url(issue)
        if issue.get(FIELD_SITE_URL) != url:
            try:
                api_patch(f"/issues/{key}", {FIELD_SITE_URL: url})
                print(f"  Updated siteUrl → {url}")
            except Exception as e:
                print(f"  WARN: could not update siteUrl: {e}")

        time.sleep(0.1)  # rate limit

    state["last_run"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    print("Done.")

if __name__ == "__main__":
    main()
