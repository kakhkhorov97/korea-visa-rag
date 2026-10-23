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


def save(name, title, text, url, pdf_sha, excerpt):
    text = text.strip()
    header = (f'---\ntitle: {title}\nsource_url: {url}\ndoc_type: law\n'
              f'retrieved: 2026-10-24\nexcerpt: {excerpt}\npdf_sha256: {pdf_sha}\n'
              f'text_sha256: {hashlib.sha256(text.encode()).hexdigest()}\n---\n')
    (DEST / f'{name}.txt').write_text(header + text + '\n', encoding='utf-8')


def main():
    decree_sha = 'c81be9d3cd10e657ddc99b70f5a4a15d0da21694510d7a741f3e704118ea2b5b'
    rules_sha = '788d80b53fdbc8c85dfc830f73c740223848e8a7bd4d0bad3da2681cedd98abc'
    text, url = download_text('169633213', decree_sha)
    lines = text.split('\n')
    # Half-open line ranges in pdftotext -layout output, checked against pages 1,3,4.
    for code, start, end in [('d2', 15, 17), ('d4', 19, 24), ('d10', 74, 81), ('e7', 105, 107)]:
        excerpt = '\n'.join(lines[start:end])
        assert {'d2': '(D-2)', 'd4': '(D-4)', 'd10': '(D-10)', 'e7': '(E-7)'}[code] in excerpt
        save(f'decree_annex_{code}', '출입국관리법 시행령 별표 1의2', excerpt, url,
             decree_sha, f'complete {code.upper()} row; PDF revised 2026-09-15')
    text, url = download_text('170812861', rules_sha)
    lines = text.split('\n')
    row = next(line[line.index('구직(D-10)'):] for line in lines if '구직(D-10)' in line)
    note = text[text.index('※'):].strip().replace('\f', '')
    save('rules_annex_d10', '출입국관리법 시행규칙 별표 1',
         lines[1].strip() + '\n체류자격(기호)    체류기간의 상한\n' + row + '\n' + note,
         url, rules_sha, 'D-10 row and full exception footnote; PDF revised 2024-12-24')


if __name__ == '__main__':
    main()
