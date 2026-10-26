"""Block common identifiers before any provider request, without retaining input.

This catches obvious patterns only. It cannot guarantee that arbitrary free text
contains no personal information. The UI must also explain the data boundary.
"""
import re

from fastapi import HTTPException

IDENTIFIERS = re.compile(
    r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}'  # email
    r'|(?<!\d)\d{6}[ -]?[1-8]\d{6}(?!\d)'  # Korean ID/registration-number shape
    r'|(?<!\d)(?:\+82[ -]?|0)1[016789][ -]?\d{3,4}[ -]?\d{4}(?!\d)'  # mobile
    r'|\b[A-Z]{1,2}\d{7,8}\b',  # common passport-number shape; never a visa code
    flags=re.I,
)


def check_question(question):
    if IDENTIFIERS.search(question):
        raise HTTPException(422, 'Remove personal identifiers such as passport/registration numbers, '
                            'phone numbers and email addresses. Ask a general visa question instead.')


def require_ai_ack(ack, required):
    if required and not ack:
        raise HTTPException(403, 'AI beta access requires the adult/South Korea and privacy acknowledgment. '
                            'You can use source-only keyword search without it.')
