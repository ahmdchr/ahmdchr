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
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]

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
        'repos': len(repos),
        'stars': sum(repo['stargazers_count'] for repo in repos),
        'followers': profile['followers'], 'following': profile['following'],
        'date': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
    }

def render(svg, stats):
    rows = {
        470: ('Public Repos', f"{stats['repos']:,}"),
        490: ('Repo Stars', f"{stats['stars']:,}  |  Followers: {stats['followers']:,}  |  Following: {stats['following']:,}"),
        510: ('Updated UTC', stats['date']),
    }
    for y, (label, value) in rows.items():
        dots = '.' * max(1, 65 - len(label) - len(value) - 5)
        fit = ' textLength="575" lengthAdjust="spacingAndGlyphs"' if len(label)+len(value)+5 > 65 else ''
        replacement = (f'<text x="390" y="{y}"{fit}><tspan class="cc">. </tspan>'
                       f'<tspan class="key">{escape(label)}</tspan>:'
                       f'<tspan class="cc"> {dots} </tspan>'
                       f'<tspan class="value">{escape(value)}</tspan></text>')
        svg, count = re.subn(rf'<text\b(?=[^>]*\bx="390")(?=[^>]*\by="{y}")[^>]*>.*?</text>',
                             lambda _: replacement, svg, flags=re.DOTALL)
        if count != 1:
            raise ValueError(f'Expected exactly one stats row at y={y}; found {count}')
    ET.fromstring(svg)
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
