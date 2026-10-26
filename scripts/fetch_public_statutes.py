"""Download selected, unmodified statutory articles from the official public viewer.

This endpoint needs no account. The selection is intentionally limited; it is not
an exhaustive immigration database. HiKorea manuals are never copied here.
"""
import hashlib
import re
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

DEST = Path(__file__).resolve().parents[1] / 'data' / 'public_raw'
ARTICLES = {
    'act': ('출입국관리법', [10, 17, 18, 20, 21, 24, 25, 31, 35, 36, 46, 94]),
    'decree': ('출입국관리법 시행령', [12, 25, 26, 30, 31]),
    'rules': ('출입국관리법 시행규칙', [34, 72, 73, 74, 76]),
}


class ArticleParser(HTMLParser):
    """Keep the viewer's lawcon paragraphs, including nested span text."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.lines = []
        self.current = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'div':
            if self.depth:
                self.depth += 1
            elif 'lawcon' in attrs.get('class', '').split():
                self.depth = 1
        if self.depth and tag == 'br':
            self.current.append('\n')

    def handle_data(self, data):
        if self.depth:
            self.current.append(data)

    def handle_endtag(self, tag):
        if self.depth and tag == 'p':
            text = re.sub(r'[ \t\r\n]+', ' ', ''.join(self.current)).strip()
            if text:
                self.lines.append(text)
            self.current = []
        if self.depth and tag == 'div':
            self.depth -= 1


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    retrieved = datetime.now(ZoneInfo('Asia/Seoul')).date().isoformat()
    for prefix, (name, numbers) in ARTICLES.items():
        for number in numbers:
            response = requests.get('https://www.law.go.kr/lsLinkProc.do',
                                    params={'lsNm': name, 'joNo': f'{number:04d}00', 'mode': '11'},
                                    timeout=30)
            response.raise_for_status()
            parser = ArticleParser()
            parser.feed(response.text)
            text = '\n'.join(parser.lines)
            if not re.match(rf'제{number}조\(', text):
                raise ValueError(f'Unexpected article response: {name} {number}')
            version = re.search(r'id="lnkLsiSeq"[^>]*value="(\d+)"', response.text)
            header = (f'---\ntitle: {name}\nsource_url: {response.url}\ndoc_type: law\n'
                      f'retrieved: {retrieved}\nstatute_version: {version.group(1) if version else "unknown"}\n'
                      f'text_sha256: {hashlib.sha256(text.encode()).hexdigest()}\n---\n')
            (DEST / f'{prefix}_{number:03d}.txt').write_text(header + text + '\n', encoding='utf-8')
            print(name, number, len(text))


if __name__ == '__main__':
    main()
