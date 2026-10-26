"""Evidence checks reject invented quotations; they do not score legal accuracy."""
import json
from types import SimpleNamespace
import pytest
from visarag.grounding import checked_claims


def payload(text='A supported explanation.', quote='공식 자료의 원문입니다.', source=1, complete=True):
    return json.dumps({'complete': complete, 'claims': [{'text': text, 'evidence': [
        {'source': source, 'quote': quote}]}]})


def test_quotes_match_across_table_whitespace_and_citations_are_programmatic():
    sources = [SimpleNamespace(text='공식 자료의\n  원문입니다.')]
    text, complete, evidence = checked_claims(payload(), sources)
    assert text == 'A supported explanation. [1]' and complete
    assert evidence[0]['source'] == 1


@pytest.mark.parametrize('raw', [payload(quote='없는 내용을 지어낸 문장입니다.'), payload(source=2),
    payload(text='An invented citation [99].'), '{"complete": true, "claims": []}',
    '{"complete": "yes", "claims": []}', 'not json'])
def test_invalid_evidence_and_payloads_are_rejected(raw):
    with pytest.raises(ValueError):
        checked_claims(raw, [SimpleNamespace(text='공식 자료의 원문입니다.')])


def test_refusal_has_no_claims_or_citations():
    text, complete, evidence = checked_claims('{"complete":false,"claims":[]}', [])
    assert text == '' and not complete and evidence == []


def test_translated_residence_code_must_match_original_pair():
    sources=[SimpleNamespace(text='거주(F-2), 동반(F-3)의 자격입니다.')]
    with pytest.raises(ValueError,match='label and code'):
        checked_claims(payload(text='The sponsor has residence (F-3).',quote='거주(F-2), 동반(F-3)의 자격입니다.'),sources)
    text,_,_=checked_claims(payload(text='The sponsor has residence (F-2).',quote='거주(F-2), 동반(F-3)의 자격입니다.'),sources)
    assert 'residence (F-2)' in text
