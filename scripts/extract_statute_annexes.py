"""Extract reviewed rows from pinned official PDFs. Requires Poppler pdftotext.

The row boundaries were checked against rendered PDF pages. Fail closed when
source bytes change; a maintainer must review the replacement layout first.
"""
import hashlib
import subprocess
import tempfile
from pathlib import Path

import requests

DEST = Path(__file__).resolve().parents[1] / 'data/public_raw'

# Half-open line ranges in the pinned pdftotext -layout output. Complete rows,
# including continuations across pages 2–7, were checked against rendered pages.
DECREE_ROWS = {
    'd2': (15, 17), 'd4': (19, 24), 'd7': (34, 50), 'd8': (50, 67),
    'd9': (67, 74), 'd10': (74, 81), 'e1': (81, 85), 'e2': (85, 89),
    'e3': (89, 94), 'e4': (94, 97), 'e5': (97, 102), 'e6': (102, 105),
    'e7': (105, 107), 'e8': (107, 111), 'e9': (111, 114),
    'f1': (125, 153), 'f2': (153, 194), 'f3': (194, 199),
    'f4': (199, 201), 'f6': (201, 209), 'h1': (209, 214),
}


def decree_rows(text):
    """Keep each legal category's exceptions attached to its definition."""
    lines = text.split('\n')
    for code, (start, end) in DECREE_ROWS.items():
        excerpt = '\n'.join(lines[start:end]).replace('\f', '').strip()
        label = f'{code[0].upper()}-{code[1:]}'
        if f'({label})' not in excerpt:
            raise ValueError(f'Missing category {label}; review the PDF layout.')
        yield code, excerpt


def download_text(file_id, expected_sha):
    url = f'https://www.law.go.kr/LSW/flDownload.do?flSeq={file_id}'
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    if hashlib.sha256(response.content).hexdigest() != expected_sha:
        raise ValueError('Official PDF changed. Review its layout before extraction.')
    with tempfile.TemporaryDirectory() as folder:
        pdf = Path(folder) / 'source.pdf'
        txt = Path(folder) / 'source.txt'
        pdf.write_bytes(response.content)
        subprocess.run(['pdftotext', '-layout', str(pdf), str(txt)], check=True)
        return txt.read_text(), url


def save(name, title, text, url, pdf_sha, excerpt, retrieved='2026-10-24'):
    text = text.strip()
    header = (f'---\ntitle: {title}\nsource_url: {url}\ndoc_type: law\n'
              f'retrieved: {retrieved}\nexcerpt: {excerpt}\npdf_sha256: {pdf_sha}\n'
              f'text_sha256: {hashlib.sha256(text.encode()).hexdigest()}\n---\n')
    (DEST / f'{name}.txt').write_text(header + text + '\n', encoding='utf-8')


def main():
    decree_sha = 'c81be9d3cd10e657ddc99b70f5a4a15d0da21694510d7a741f3e704118ea2b5b'
    rules_sha = '788d80b53fdbc8c85dfc830f73c740223848e8a7bd4d0bad3da2681cedd98abc'
    text, url = download_text('169633213', decree_sha)
    for code, excerpt in decree_rows(text):
        save(f'decree_annex_{code}', '출입국관리법 시행령 별표 1의2', excerpt, url,
             decree_sha, f'complete {code.upper()} row; PDF revised 2026-09-15',
             retrieved='2026-10-24' if code in {'d2', 'd4', 'd10', 'e7'} else '2026-10-26')
    text, url = download_text('170812861', rules_sha)
    lines = text.split('\n')
    row = next(line[line.index('구직(D-10)'):] for line in lines if '구직(D-10)' in line)
    note = text[text.index('※'):].strip().replace('\f', '')
    save('rules_annex_d10', '출입국관리법 시행규칙 별표 1',
         lines[1].strip() + '\n체류자격(기호)    체류기간의 상한\n' + row + '\n' + note,
         url, rules_sha, 'D-10 row and full exception footnote; PDF revised 2024-12-24')


if __name__ == '__main__':
    main()
