# United Arab Emirates — LawCodex (تشريعات دولة الإمارات العربية المتحدة)

UAE federal legislation as plain Markdown: Arabic texts (`ar/`), plus the official English
versions (`en/`) where the portal publishes one. Part of [LawCodex](https://github.com/LawCodex):
one repository per jurisdiction.

> **Partial coverage, built from Internet Archive copies of the official portal.** The official
> source is the **UAE Legislation** platform (منصة التشريعات), run by the General Secretariat of
> the Cabinet, at [uaelegislation.gov.ae](https://uaelegislation.gov.ae). It answers every
> automated request with a Cloudflare bot challenge (HTTP 403), and LawCodex does not circumvent
> such challenges. Each text here was therefore taken from the **latest usable Wayback Machine
> capture** of its official page. Every file records the official URL (`source`), the archived
> copy (`archived_source`) and the capture date (`archived`). Only pages that the Internet
> Archive happened to capture are covered. Check the official portal before you rely on a text.

- Retrieved: **2026-10-13**. Capture dates range from 2024 to 2026; most are from 2025.
- Version: the portal publishes **consolidated** texts. Each page states "التشريع وفقاً لآخر تحديث
  في" / "the last update on this law was listed on", which is recorded as `last_amended`.
  Amended articles appear in their current wording. The portal's "previous texts" pop-ups
  (النصوص السابقة) are not included.

## Coverage

| Directory | Type | Arabic | English |
| --- | --- | ---: | ---: |
| `constitution/` | دستور دولة الإمارات العربية المتحدة: the Constitution of 1971, as amended up to 2023 | 1 | 1 |
| `federal-laws/<year>/` | قانون اتحادي: federal laws | 67 | 44 |
| `federal-decree-laws/<year>/` | مرسوم بقانون اتحادي: federal decree-laws (e.g. Crimes and Penalties, Commercial Companies, Labour Relations, Evidence, Personal Status, Copyright) | 82 | 62 |
| `federal-decrees/<year>/` | مرسوم اتحادي: federal decrees | 2 | 1 |
| `cabinet-resolutions/<year>/` | قرار مجلس الوزراء: Cabinet resolutions (incl. executive regulations) | 170 | 93 |
| `ministerial-resolutions/<year>/` | قرار وزاري: ministerial resolutions | 5 | 1 |
| `other/<year>/` | a board chairman's decision issuing the executive regulation of Federal Law 9/2011 on land transport | 1 | 0 |
| **Total** | | **328** | **202** |

All files carry the portal's status. Every captured page says ساري / Active (`in_force`), except
one with no status (`unknown`).

### Not covered / known gaps

- **Most federal legislation is missing.** The portal lists several thousand federal instruments.
  The Internet Archive has captured only about 330 legislation pages in Arabic and 225 in English,
  and 28 of those captures hold only the page frame without the article text (the text is loaded
  later by JavaScript). Those 28 were skipped. A complete corpus needs direct access to the portal
  (e.g. an allow-listed client or permission from the General Secretariat of the Cabinet).
- Preambles are loaded separately by the portal (`/preamble`) and are usually missing from the
  captures.
- Annexes and attachments published as PDF (`/download`) are not included.
- Local (emirate-level) legislation is not covered. Abu Dhabi, Dubai and the other emirates
  publish their own legislation.

## Structure and file names

```
ar/constitution/constitution-1971.md
ar/<type>/<year>/<year>-<number>.md
en/...  (same layout and file names as ar/)
```

File names come from the official number and year in the title (e.g. Federal Decree-Law No. 38
of 2021 → `federal-decree-laws/2021/2021-38.md`). Front matter: `title` (official title with
number), `identifier` (`<type>/<year>/<number>`), `uaelegislation_id` (the portal's page id),
`type`, `date` (issue date), `effective`, `last_amended`, `status`, `gazette` (Official Gazette
issue and date), `source`, `archived_source`, `archived`, `retrieved`.

The portal's parts and chapters (الباب / الفصل) are headings, and each article (المادة) is a
heading one level below.

## Licence

Under Article 3 of Federal Decree-Law No. 38 of 2021 on Copyright and Neighbouring Rights
([`ar/federal-decree-laws/2021/2021-38.md`](ar/federal-decree-laws/2021/2021-38.md)), copyright
does not protect "official documents, whatever their original language or the language into
which they have been translated, such as texts of laws, regulations, decisions, international
agreements, judicial rulings …". The portal's terms and conditions do not restrict the reuse of
its content (they forbid attacks on, and overloading of, the site). The Arabic text prevails over
the English version.

## Regenerating

```sh
pip install -r scripts/requirements.txt
python scripts/ae_fetch.py  /path/to/raw     # CDX listings + latest usable Wayback captures (cached)
python scripts/ae_convert.py /path/to/raw .  # writes ar/ and en/
```

`ae_fetch.py` requests the Wayback Machine one page at a time, about one request every 1.5 s, and
identifies itself as `LawCodex/1.0`.
