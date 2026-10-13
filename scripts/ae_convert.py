#!/usr/bin/env python3
"""Convert archived uaelegislation.gov.ae pages (see ae_fetch.py) to LawCodex Markdown.

Usage: ae_convert.py RAW_DIR REPO_DIR
"""
import collections, datetime, glob, json, os, re, sys
from bs4 import BeautifulSoup, NavigableString, Tag

TODAY = datetime.date.today().isoformat()
AR_DIGITS = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
MONTHS = {m: i + 1 for i, m in enumerate(
    ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'])}
MONTHS.update({m: i + 1 for i, m in enumerate(
    ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])})
MONTHS['إبريل'] = 4
# (regex on title, directory, type)
KINDS = [
    (r'^دستور|^The Constitution', 'constitution', 'constitution'),
    (r'^(?:ال)?مرسوم\s*بقانون\s*اتحادي|^Federal Decree[- ]by[- ]Law|^Federal Decree[- ]Law', 'federal-decree-laws', 'federal_decree_law'),
    (r'^(?:ال)?قانون\s*(?:ال)?اتحادي|^Federal Law', 'federal-laws', 'federal_law'),
    (r'^مرسوم\s*اتحادي|^Federal Decree', 'federal-decrees', 'federal_decree'),
    (r'^ق\S*رار\s*مجلس\s*الوزراء|^Cabinet (Resolution|Decision)', 'cabinet-resolutions', 'cabinet_resolution'),
    (r'^قرار\s*وزاري|^Ministerial (Resolution|Decision)', 'ministerial-resolutions', 'ministerial_resolution'),
]
LABELS = {
    'تاريخ إصدار التشريع': 'date', 'Issued Date': 'date', 'Issue Date': 'date',
    'تاريخ نفاذ التشريع': 'effective', 'Effective Date': 'effective',
    'تاريخ الجريدة الرسمية': 'gazette_date', 'Official Gazette Date': 'gazette_date',
    'عدد الجريدة الرسمية': 'gazette_number', 'Official Gazette No': 'gazette_number',
    'حالة التشريع': 'status', 'Legislation State': 'status',
}
STATUS = {'ساري': 'in_force', 'Active': 'in_force', 'ملغى': 'repealed', 'ملغي': 'repealed',
          'Repealed': 'repealed', 'Cancelled': 'repealed'}


def clean(s):
    return re.sub(r'[ \t\u00a0\u200b\r]+', ' ', s).strip()


def yq(s):
    return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ') + '"'


def inline(node):
    out = []
    for c in node.children:
        if isinstance(c, NavigableString):
            if c.__class__.__name__ in ('Comment', 'Doctype', 'ProcessingInstruction'):
                continue
            out.append(re.sub(r'\s+', ' ', str(c)))
        elif isinstance(c, Tag):
            n = c.name.lower()
            if n == 'br':
                out.append('\n')
            elif n in ('script', 'style', 'svg', 'img', 'button', 'form'):
                continue
            elif 'tooltip_holder' in (c.get('class') or []):
                continue
            elif n in ('strong', 'b'):
                t = inline(c).strip()
                out.append(f'**{t}**' if t and '\n' not in t and '**' not in t else t)
            elif n == 'table':
                out.append('\n\n' + table(c) + '\n\n')
            elif n in ('p', 'div', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'center', 'tr', 'blockquote'):
                out.append('\n\n' + inline(c) + '\n\n')
            else:
                out.append(inline(c))
    return ''.join(out)


def table(t):
    rows = []
    for tr in t.find_all('tr'):
        cells = tr.find_all(['td', 'th'], recursive=False)
        if any(c.get('rowspan') or c.get('colspan') for c in cells):
            for tag in t.find_all(True):
                tag.attrs = {k: v for k, v in tag.attrs.items() if k in ('rowspan', 'colspan')}
            return re.sub(r'\s+', ' ', str(t))
        rows.append([clean(inline(c)).replace('\n', '<br>').replace('|', '\\|') for c in cells])
    rows = [r for r in rows if r]
    if not rows:
        return ''
    n = max(len(r) for r in rows)
    rows = [r + [''] * (n - len(r)) for r in rows]
    md = ['| ' + ' | '.join(rows[0]) + ' |', '|' + ' --- |' * n]
    md += ['| ' + ' | '.join(r) + ' |' for r in rows[1:]]
    return '\n'.join(md)


def paras(node):
    lines = [clean(l) for l in inline(node).split('\n')]
    return '\n\n'.join(l for l in lines if l and l not in ('**', '****'))


def parse_date(s):
    s = clean(s.translate(AR_DIGITS))
    m = re.search(r'(\d{1,2})\s+(\S+)\s+(\d{4})', s)
    if not m:
        return None
    mon = MONTHS.get(m.group(2)) or MONTHS.get(m.group(2)[:3].lower())
    if not mon:
        return None
    try:
        return datetime.date(int(m.group(3)), mon, int(m.group(1))).isoformat()
    except ValueError:
        return None


def meta(s):
    strings = list(s.stripped_strings)
    info = {}
    for i, x in enumerate(strings[:-1]):
        k = LABELS.get(x)
        if k and k not in info:
            info[k] = strings[i + 1]
        if (x.startswith('التشريع وفقاً لآخر تحديث') or x.startswith('The last update')) and 'last_amended' not in info:
            info['last_amended'] = parse_date(x) or parse_date(strings[i + 1])
    return info


def body(s):
    root = s.select_one('.law_main_content')
    heads = [h for h in root.find_all(['h2', 'h3', 'h4', 'h5'])
             if 'text_center' in (h.get('class') or []) and not h.find_parent(class_='title_')]
    tags = sorted({h.name for h in heads})
    lvl = {t: 2 + i for i, t in enumerate(tags)}
    cur = [1]
    out = []
    pre = root.find(id='preamble')
    if pre is not None:
        t = paras(pre)
        if t:
            out.append(t)

    def walk(node):
        for c in node.find_all(recursive=False):
            cls = c.get('class') or []
            if 'title_' in cls or 'law_image_box' in cls or c.get('id') == 'preamble':
                continue
            if c in heads:
                t = clean(c.get_text(' ', strip=True))
                if t:
                    out.append('#' * lvl[c.name] + ' ' + t)
                    cur[0] = lvl[c.name]
                continue
            if 'content_' in cls and (c.get('id') or '').startswith('item'):
                h = c.select_one('.c_title')
                if h:
                    for tip in h.select('.tooltip_holder'):
                        tip.decompose()
                    t = clean(h.get_text(' ', strip=True))
                    if t:
                        out.append('#' * min(cur[0] + 1, 6) + ' ' + t)
                for ta in c.select('.text_area'):
                    t = paras(ta)
                    if t:
                        out.append(t)
                continue
            if c.name in ('script', 'style', 'svg'):
                continue
            walk(c)
    walk(root)
    return '\n\n'.join(out)


def classify(title):
    for rx, d, t in KINDS:
        if re.search(rx, title.strip(), re.I):
            return d, t
    return 'other', 'other'


def number_year(title):
    t = title.translate(AR_DIGITS)
    m = (re.search(r'رق\S*م\s*\(?\s*(\d+)\s*\)?\s*لس\S*نة\s*(\d{4})', t) or
         re.search(r'No\.?\s*\(?\s*(\d+)\s*\)?\s*(?:of|for|/)\s*(\d{4})', t, re.I))
    return (m.group(1), m.group(2)) if m else (None, None)


def load(raw, lid, lang):
    f = os.path.join(raw, 'html', f'{lid}_{lang}.html')
    if not os.path.exists(f):
        return None
    html = open(f, encoding='utf-8').read()
    if 'law_main_content' not in html:
        return None
    s = BeautifulSoup(html, 'lxml')
    t = s.select_one('.law_main_content .title_')
    title = clean(t.get_text(' ', strip=True)) if t else ''
    if not title:
        title = clean(s.title.get_text().split('|', 1)[-1]) if s.title else lid
    return s, title, json.load(open(f[:-5] + '.json'))


def main():
    raw, repo = sys.argv[1], sys.argv[2]
    ids = sorted({os.path.basename(f).rsplit('_', 1)[0] for f in glob.glob(os.path.join(raw, 'html', '*.html'))})
    counts = collections.Counter()
    used = collections.Counter()
    for lid in ids:
        docs = {lang: load(raw, lid, lang) for lang in ('ar', 'en')}
        base = docs['ar'] or docs['en']
        if not base:
            print('SKIP (no content)', lid, file=sys.stderr)
            continue
        d, typ = classify(base[1])
        num, year = number_year(base[1])
        if d == 'constitution':
            rel, slug = 'constitution', 'constitution-1971'
            if used[(rel, slug)]:  # /constitution duplicates legislation 1000, which keeps the part headings
                continue
        elif num:
            rel, slug = f'{d}/{year}', f'{year}-{num}'
        else:
            info = meta(base[0])
            y = (parse_date(info.get('date', '')) or 'unknown')[:4]
            rel, slug = f'{d}/{y}', f'{y}-uaelegislation-{lid}'
        if used[(rel, slug)]:
            slug = f'{slug}-{lid}'
        used[(rel, slug)] += 1
        for lang, doc in docs.items():
            if not doc:
                continue
            s, title, cap = doc
            b = body(s)
            if len(b) < 40:
                print('EMPTY', lid, lang, file=sys.stderr)
                continue
            info = meta(s)
            status = STATUS.get(info.get('status', ''), 'unknown')
            fm = ['---', f'title: {yq(title)}',
                  f'identifier: {yq(f"{typ}/{year}/{num}" if num else lid)}',
                  f'uaelegislation_id: {yq(lid)}', f'type: {typ}', 'jurisdiction: ae', f'language: {lang}']
            for k in ('date', 'effective'):
                v = parse_date(info.get(k, ''))
                if v:
                    fm.append(f'{k}: {v}')
            if info.get('last_amended'):
                fm.append(f'last_amended: {info["last_amended"]}')
            fm.append(f'status: {status}')
            g = parse_date(info.get('gazette_date', ''))
            if info.get('gazette_number') or g:
                fm.append(f'gazette: {yq(", ".join(x for x in ["No. " + info["gazette_number"] if info.get("gazette_number") else "", g or ""] if x))}')
            src = (f'https://uaelegislation.gov.ae/{lang}/constitution' if lid == 'constitution'
                   else f'https://uaelegislation.gov.ae/{lang}/legislations/{lid}')
            fm += [f'source: {yq(src)}', f'archived_source: {yq(cap["archive_url"])}',
                   f'archived: {cap["timestamp"][:4]}-{cap["timestamp"][4:6]}-{cap["timestamp"][6:8]}',
                   f'retrieved: {TODAY}']
            if lang == 'en':
                fm.append('translation: "English version published by the UAE Legislation portal; the Arabic text prevails"')
            fm.append('---')
            path = os.path.join(repo, lang, rel, slug + '.md')
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8', newline='\n') as fh:
                fh.write('\n'.join(fm) + '\n\n# ' + title + '\n\n' + b.strip() + '\n')
            counts[(lang, rel.split('/')[0], status)] += 1
    for k in sorted(counts):
        print(*k, counts[k])


if __name__ == '__main__':
    main()
