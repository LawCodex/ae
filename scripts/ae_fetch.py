#!/usr/bin/env python3
"""Fetch UAE federal legislation pages from Internet Archive copies of uaelegislation.gov.ae.

uaelegislation.gov.ae answers automated clients with a Cloudflare challenge (HTTP 403), which
LawCodex does not circumvent; the latest Wayback Machine capture of each page is used instead.

Usage: ae_fetch.py RAW_DIR
  RAW_DIR/cdx_<lang>.txt, cdx_const.txt   CDX listings (downloaded if missing)
  RAW_DIR/html/<id>_<lang>.html (+ .json)  cached captures; id "constitution" for the constitution
"""
import json, os, re, sys, time
import requests

UA = 'LawCodex/1.0 (+https://github.com/LawCodex)'
CDX = 'https://web.archive.org/cdx/search/cdx?fl=original,timestamp,statuscode,mimetype,length&filter=statuscode:200'
S = requests.Session()
S.headers['User-Agent'] = UA


def get(url, timeout=180):
    delay = 10
    for attempt in range(12):
        try:
            r = S.get(url, timeout=timeout)
            if r.status_code == 200:
                return r
            if r.status_code == 404:
                return None
            print('  HTTP', r.status_code, url, file=sys.stderr, flush=True)
        except requests.RequestException as e:
            print('  ERR', type(e).__name__, url, file=sys.stderr, flush=True)
        time.sleep(delay)
        delay = min(delay * 2, 300)
    return None


def cdx(raw, name, query):
    path = os.path.join(raw, name)
    if not os.path.exists(path):
        open(path, 'w').write(get(CDX + '&' + query, timeout=600).text)
    for line in open(path):
        p = line.split()
        if len(p) >= 5:
            yield p[0], p[1], int(p[4]) if p[4].isdigit() else 0


def main():
    raw = sys.argv[1]
    os.makedirs(os.path.join(raw, 'html'), exist_ok=True)
    caps = {}
    for lang in ('ar', 'en'):
        for u, ts, ln in cdx(raw, f'cdx_{lang}.txt',
                             f'url=uaelegislation.gov.ae/{lang}/legislations/&matchType=prefix&filter=mimetype:text/html'):
            m = re.search(r'/legislations/(\d+)/?$', u)
            if m:
                caps.setdefault((m.group(1), lang), []).append((ts, ln, u))
    for u, ts, ln in cdx(raw, 'cdx_const.txt',
                         'url=uaelegislation.gov.ae/&matchType=prefix&filter=original:.*constitution.*'):
        m = re.search(r'gov\.ae/(ar|en)/constitution/?$', u)
        if m:
            caps.setdefault(('constitution', m.group(1)), []).append((ts, ln, u))
    todo = sorted(caps)
    print(len(todo), 'pages', flush=True)
    for i, (lid, lang) in enumerate(todo):
        out = os.path.join(raw, 'html', f'{lid}_{lang}.html')
        if os.path.exists(out):
            continue
        cands = sorted(caps[(lid, lang)], reverse=True)
        cands = [c for c in cands if c[1] >= 20000] or cands
        for ts, ln, u in cands[:8]:
            r = get(f'https://web.archive.org/web/{ts}id_/{u}')
            time.sleep(1.5)
            if r is None:
                continue
            html = r.content.decode('utf-8', 'replace')
            if 'challenge-platform' in html and 'Just a moment' in html:
                continue
            if 'c_title' not in html and lid != 'constitution':  # capture without article text
                continue
            open(out, 'w', encoding='utf-8').write(html)
            json.dump({'id': lid, 'lang': lang, 'timestamp': ts, 'original': u,
                       'archive_url': f'https://web.archive.org/web/{ts}/{u}'}, open(out[:-5] + '.json', 'w'))
            print(i, lid, lang, ts, flush=True)
            break
        else:
            print(i, lid, lang, 'NO USABLE CAPTURE', flush=True)


if __name__ == '__main__':
    main()
