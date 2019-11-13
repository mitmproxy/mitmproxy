from mitmproxy import lexer
import pytest


class TestScripts:

    def test_simple(self):

        cases = [
            {
                "text": r'abc',
                "result": ['abc']
            },
            {
                "text": r'"Hello \" Double Quotes"',
                "result": ['"Hello \\" Double Quotes"']
            },
            {
                "text": r"'Hello \' Single Quotes'",
                "result": ["'Hello \\' Single Quotes'"]
            },
            {
                "text": r'"\""',
                "result": ['"\\""']
            },
            {
                "text": r'abc "def\" \x bla \z \\ \e \ " xpto',
                "result": ['abc', '"def\\" \\x bla \\z \\\\ \\e \\ "', 'xpto']
            },
            {
                "text": r'',
                "result": []
            },
            {
                "text": r' ',
                "result": []
            },
            {
                "text": r'  ',
                "result": []
            },
            {
                "text": r'Space in the end ',
                "result": ['Space', 'in', 'the', 'end']
            },
            {
                "text": '\n\n\rHello\n World With Spaces\n\n',
                "result": ['Hello', 'World', 'With', 'Spaces']
            },
        ]

        for t in cases:

            lex = lexer.Lexer(t['text'])
            tokens = list(lex)
            result = t['result']
            assert(tokens == result)

    def test_fail(self):
        text = r'"should fail with missing closing quote'
        lex = lexer.Lexer(text)
        with pytest.raises(ValueError, match="No closing quotation"):
            assert list(lex)

