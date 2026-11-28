import datetime as dt
import json
from collections import Counter
from html import escape
from pathlib import Path
import subprocess

def query(body):
    result = subprocess.check_output(['gh', 'api', 'graphql', '-f', 'query=' + body], encoding='utf8')
    return json.loads(result)['data']['user']

def card(filename, metrics):
    accent, heading = {
        'activity': ('#ce77ff', 'Overview'),
        'languages': ('#16efff', 'Languages'),
        'streak': ('#ffae37', 'Streaks'),
    }[filename]
    tint = {'activity': '#6020b0', 'languages': '#075eaa', 'streak': '#a52a60'}[filename]
    labels = {
        'Public non-fork repositories': 'Public non-fork repos',
        'Stars across these repositories': 'Repository stars',
        'Calendar contributions Â· 365 days': 'Contributions',
    }
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="284" height="180" viewBox="0 0 284 180" font-family="Segoe UI,Arial,sans-serif">',
             f'<defs><linearGradient id="bg" x2="1" y2="1"><stop stop-color="{tint}"/><stop offset=".7" stop-color="#131128"/></linearGradient></defs>',
             '<rect width="284" height="180" rx="18" fill="url(#bg)"/>',
             f'<circle cx="23" cy="29" r="6" fill="{accent}"/>',
             f'<text x="38" y="36" fill="{accent}" font-size="23" font-weight="700">{heading}</text>']
    for i, (label, value) in enumerate(metrics):
        y = 75 + i * 39
        label = labels.get(label, label)
        parts.append(f'<path d="M18 {y+12}h248" stroke="#34334c"/>')
        parts.append(f'<text x="18" y="{y}" fill="#edeafb" font-size="16">{escape(label)}</text>')
        parts.append(f'<text x="264" y="{y}" text-anchor="end" fill="{accent}" font-weight="700" font-size="20">{escape(str(value))}</text>')
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
card('activity',[('Public non-fork repositories',len(repos)),('Stars across these repositories',sum(r['stargazerCount'] for r in repos)),('Calendar contributions Â· 365 days',sum(n for _, n in days))])
card('languages',[(name,f'{100*size/sum(langs.values()):.1f}%') for name,size in langs.most_common(3)])
card('streak',[('Current streak',f'{current} days'),('Longest streak',f'{longest} days'),('Days with contributions',sum(n>0 for _,n in days))])

# Each column represents one Monday-start calendar week. The last is in progress.
monday = today - dt.timedelta(days=today.weekday())
starts = [monday - dt.timedelta(weeks=offset) for offset in reversed(range(26))]
totals = dict.fromkeys(starts, 0)
for date, count in days:
    day = dt.date.fromisoformat(date)
    week = day - dt.timedelta(days=day.weekday())
    if week in totals:
        totals[week] += count

peak = max(totals.values())
parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 860 230" font-family="Segoe UI,Arial,sans-serif">',
         '<rect width="860" height="230" rx="20" fill="#100e25"/>',
         '<text x="26" y="39" font-size="24" font-weight="700" fill="white">Weekly contributions</text>',
         f'<text x="835" y="38" text-anchor="end" font-size="17" fill="#a6dfff">26 weeks · Peak {peak}</text>']
palette = ['#5551ff', '#932cff', '#ff238c', '#ff8424']
for i, (week, count) in enumerate(totals.items()):
    x = 28 + i * 31
    height = 105 * count / max(1, peak)
    y = 175 - height
    color = palette[min(3, int(4 * count / max(1, peak)))]
    parts.append(f'<g><title>Week of {week}: {count} contributions</title>')
    if count:
        parts.append(f'<path d="M{x} {y:.1f}h18V175h-18Z" fill="{color}"/>')
        parts.append(f'<path d="M{x+18} {y:.1f}l6 -4V171l-6 4Z" fill="{color}" opacity=".66"/>')
    parts.append(f'<path d="M{x} {y:.1f}l6 -4h18l-6 4Z" fill="{color if count else "#343653"}"/></g>')
for index in (0, 8, 17, 25):
    label = starts[index].strftime('%d %b')
    parts.append(f'<text x="{28 + index * 31}" y="207" font-size="15" fill="#c4c9e8">{label}</text>')
Path('assets/folio/weekly.svg').write_text(''.join(parts)+'</svg>', encoding='utf8')
