from mitmproxy import lexer
import pytest
import io


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
            {
                "text": r'\" Escaping characters without reason',
                "result": ['\\"', 'Escaping', 'characters', 'without', 'reason']
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

    def test_stringio_text(self):
        text = io.StringIO(r'Increase test coverage')
        lex = lexer.Lexer(text)
        tokens = list(lex)
        result = ['Increase', 'test', 'coverage']
        assert(tokens == result)


