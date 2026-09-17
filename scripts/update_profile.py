"""Refresh public profile stats without changing the ASCII portrait."""
import json
import os
from pathlib import Path
import re
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from html import escape
from urllib.parse import quote
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]

def line_totals(username, repos):
    """Count user-authored commits reachable on owned public default branches.

    Cache immutable commit stats; enumerate history afresh so deleted or
    rewritten commits do not remain in the totals. Shared SHAs count once.
    """
    cache_path = ROOT / '.cache' / 'commit-stats.json'
    try:
        cache = json.loads(cache_path.read_text(encoding='utf-8'))
    except (FileNotFoundError, ValueError):
        cache = {}
    seen = set()
    added = deleted = commits = 0
    for repo in repos:
        full_name = repo['full_name']
        page = 1
        while True:
            path = (f'/repos/{full_name}/commits?author={quote(username)}'
                    f'&sha={quote(repo["default_branch"], safe="")}&per_page=100&page={page}')
            try:
                batch = api(path)
            except HTTPError as error:
                if error.code == 409:  # Repository has no Git history.
                    break
                raise
            for commit in batch:
                sha = commit['sha']
                author = commit.get('author') or {}
                if author.get('login', '').casefold() != username.casefold() or sha in seen:
                    continue
                seen.add(sha)
                if sha not in cache:
                    detail = api(f'/repos/{full_name}/commits/{sha}')
                    cache[sha] = {
                        'additions': detail['stats']['additions'],
                        'deletions': detail['stats']['deletions'],
                    }
                added += cache[sha]['additions']
                deleted += cache[sha]['deletions']
                commits += 1
            if len(batch) < 100:
                break
            page += 1
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, sort_keys=True), encoding='utf-8')
    return {'added': added, 'deleted': deleted, 'net': added-deleted, 'commits': commits}

def api(path):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'ahmdchr-profile',
               'X-GitHub-Api-Version': '2022-11-28'}
    if os.getenv('GH_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    for attempt in range(3):
        try:
            with urlopen(Request('https://api.github.com' + path, headers=headers), timeout=30) as response:
                return json.load(response)
        except HTTPError as error:
            if error.code < 500 or attempt == 2:
                raise
            time.sleep(2 ** attempt)

def collect(username):
    profile = api('/users/' + username)
    repos = []
    page = 1
    while True:
        batch = api(f'/users/{username}/repos?type=owner&per_page=100&page={page}')
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return {
        **line_totals(username, repos),
        'repos': len(repos),
        'stars': sum(repo['stargazers_count'] for repo in repos),
        'followers': profile['followers'], 'following': profile['following'],
        'date': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
    }

def render(svg, stats):
    rows = {
        470: ('Public Repos', f"{stats['repos']:,}  |  Stars: {stats['stars']:,}"),
        490: ('Commits', f"{stats['commits']:,}  |  Followers: {stats['followers']:,}"),
        510: ('Lines (net)', f"{stats['net']:,} ({stats['added']:,}++, {stats['deleted']:,}--)"),
    }
    for y, (label, value) in rows.items():
        dots = '.' * max(1, 65 - len(label) - len(value) - 5)
        fit = ' textLength="575" lengthAdjust="spacingAndGlyphs"' if len(label)+len(value)+5 > 65 else ''
        replacement = (f'<text x="390" y="{y}"{fit}><tspan class="cc">. </tspan>'
                       f'<tspan class="key">{escape(label)}</tspan>:'
                       f'<tspan class="cc"> {dots} </tspan>'
                       f'<tspan class="value">{escape(value)}</tspan></text>')
        if y == 510:
            dark = 'fill="#161b22"' in svg
            green, red = ('#3fb950', '#f85149') if dark else ('#1a7f37', '#cf222e')
            replacement = replacement.replace(f"{stats['added']:,}++", f'<tspan fill="{green}">{stats["added"]:,}++</tspan>')
            replacement = replacement.replace(f"{stats['deleted']:,}--", f'<tspan fill="{red}">{stats["deleted"]:,}--</tspan>')
        svg, count = re.subn(rf'<text\b(?=[^>]*\bx="390")(?=[^>]*\by="{y}")[^>]*>.*?</text>',
                             lambda _: replacement, svg, flags=re.DOTALL)
        if count != 1:
            raise ValueError(f'Expected exactly one stats row at y={y}; found {count}')
    ET.fromstring(svg)
    svg = re.sub(r'<!-- Stats updated UTC: .*? -->\n?', '', svg)
    svg = svg.replace('</svg>', f'<!-- Stats updated UTC: {stats["date"]} -->\n</svg>')
    return svg

def main():
    username = os.environ.get('PROFILE_USER', 'ahmdchr')
    if not re.fullmatch(r'[A-Za-z0-9-]+', username):
        raise ValueError('Invalid GitHub username')
    stats = collect(username)
    # Validate both results before writing either file; failed API calls never
    # replace good statistics with zeroes.
    updated = {}
    for name in ('dark_mode_v2.svg', 'light_mode_v2.svg'):
        path = ROOT / name
        updated[path] = render(path.read_text(encoding='utf-8'), stats)
    for path, contents in updated.items():
        path.write_text(contents, encoding='utf-8')
    print('Updated public GitHub statistics:', json.dumps(stats))

if __name__ == '__main__':
    main()
