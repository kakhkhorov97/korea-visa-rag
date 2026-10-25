"""Public category coverage and complete legal exceptions, without API calls."""
import hashlib
from pathlib import Path

from visarag.chunking import chunk_document
from visarag.documents import load_documents

RAW = Path(__file__).resolve().parents[1] / 'data/public_raw'


def test_reviewed_categories_have_provenance_and_intact_rows():
    expected = {'d2', 'd4', 'd7', 'd8', 'd9', 'd10',
                *(f'e{i}' for i in range(1, 10)),
                'f1', 'f2', 'f3', 'f4', 'f6', 'h1'}
    docs = {d.doc_id.removeprefix('decree_annex_'): d
            for d in load_documents(RAW) if d.doc_id.startswith('decree_annex_')}
    assert set(docs) == expected
    for code, doc in docs.items():
        assert doc.doc_type == 'law' and doc.retrieved
        assert doc.source_url == 'https://www.law.go.kr/LSW/flDownload.do?flSeq=169633213'
        assert doc.extra['text_sha256'] == hashlib.sha256(doc.text.encode()).hexdigest()
        assert f'({code[0].upper()}-{code[1:]})' in doc.text
        assert len(chunk_document(doc)) == 1  # No severed conditions or exceptions.
    assert '재외동포(F-4)' in docs['f3'].text
    assert '타목의 체류' in docs['f3'].text and '제외한다' in docs['f3'].text
    assert '파.' in docs['f2'].text and '인구감소지역' in docs['f2'].text
    assert '책임이 없는' in docs['f6'].text and '정상적인 혼인관계' in docs['f6'].text
    assert '협정' in docs['h1'].text and '제외한다' in docs['h1'].text
    assert '지식재산권' in docs['d8'].text and '추천한 사람' in docs['d8'].text
