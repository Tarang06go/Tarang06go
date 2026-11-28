import datetime as dt
import json
from collections import Counter
from html import escape
from pathlib import Path
import subprocess

def query(body):
    result = subprocess.check_output(['gh', 'api', 'graphql', '-f', 'query=' + body], encoding='utf8')
    return json.loads(result)['data']['user']

def card(filename, title, metrics):
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="440" height="134" viewBox="0 0 440 134" font-family="Segoe UI,Arial,sans-serif">',
             '<rect width="440" height="134" rx="12" fill="#101419"/>',
             f'<text x="20" y="29" fill="#99e1cf" font-size="16">{escape(title)}</text>']
    for i, (label, value) in enumerate(metrics):
        y = 58 + i * 28
        parts.append(f'<text x="20" y="{y}" fill="#c5cdd1" font-size="18">{escape(label)}</text>')
        parts.append(f'<text x="418" y="{y}" text-anchor="end" fill="#f2f4f1" font-size="20">{escape(str(value))}</text>')
    Path(f'assets/folio/{filename}.svg').write_text(''.join(parts)+'</svg>', encoding='utf8')

user = 'Tarang06go'
today = dt.datetime.now(dt.timezone.utc).date()
calendar = query(f'{{user(login:"{user}"){{contributionsCollection{{contributionCalendar{{weeks{{contributionDays{{date contributionCount}}}}}}}}}}}}')
days = sorted((d['date'], d['contributionCount']) for w in calendar['contributionsCollection']['contributionCalendar']['weeks'] for d in w['contributionDays'] if d['date'] <= today.isoformat())[-365:]
streak = longest = current = 0
for date, count in days:
    streak = streak + 1 if count else 0
    longest = max(longest, streak)
    if count or date != today.isoformat():
        current = streak
langs = Counter()
repos = []
cursor = 'null'
while True:
    data = query(f'{{user(login:"{user}"){{repositories(first:100,after:{cursor},privacy:PUBLIC,isFork:false,ownerAffiliations:OWNER){{pageInfo{{hasNextPage endCursor}} nodes{{name stargazerCount languages(first:100){{totalCount edges{{size node{{name}}}}}}}}}}}}}}')['repositories']
    for repo in data['nodes']:
        repos.append(repo)
        details = repo['languages']
        if details['totalCount'] > len(details['edges']):
            raise ValueError('Language list truncated')
        for edge in details['edges']:
            langs[edge['node']['name']] += edge['size']
    if not data['pageInfo']['hasNextPage']:
        break
    cursor = json.dumps(data['pageInfo']['endCursor'])
card('activity','GitHub overview',[('Public non-fork repositories',len(repos)),('Stars across these repositories',sum(r['stargazerCount'] for r in repos)),('Calendar contributions · 365 days',sum(n for _, n in days))])
card('languages','Top languages · share of detected bytes',[(name,f'{100*size/sum(langs.values()):.1f}%') for name,size in langs.most_common(3)])
card('streak','Contribution streaks · trailing 365 days',[('Current streak',f'{current} days'),('Longest streak',f'{longest} days'),('Days with contributions',sum(n>0 for _,n in days))])
