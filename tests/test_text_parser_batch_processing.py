"""Regression tests for text chunking and JSON Lines file processing."""

import ast
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ProcessingError(Exception):
    """Represent the application's logged processing error."""


class FakeDataFrame:
    """Capture the Data column and workbook-writing contract.

    Attributes:
        records (list[str]): Chunk rows supplied to the Data column.
        columns (list[str]): Names of the DataFrame columns.
    """

    def __init__(self, records: list[str], columns: list[str]) -> None:
        """Initialize the small DataFrame stand-in."""
        self.records = records
        self.columns = columns

    def to_excel(self, path: str, sheet_name: str, index: bool,
                 columns: list[str]) -> None:
        """Record an output workbook without requiring optional Excel engines."""
        if sheet_name != 'Dataset' or columns != ['Data'] or index:
            raise AssertionError('Workbook output contract changed.')
        Path(path).write_text('\n'.join(self.records), encoding='utf-8')


class TextParserBatchTests(unittest.TestCase):
    """Verify batch processing outputs and input validation."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load production functions without importing optional NLP dependencies."""
        tree = ast.parse((ROOT / 'processors.py').read_text(encoding='utf-8'))
        guard = next(node for node in tree.body
                     if isinstance(node, ast.FunctionDef) and node.name == 'throw_if')
        parser = next(node for node in tree.body
                      if isinstance(node, ast.ClassDef) and node.name == 'TextParser')
        names = {'chunk_datasets', 'convert_jsonl'}
        methods = [node for node in parser.body
                   if isinstance(node, ast.FunctionDef) and node.name in names]
        if {node.name for node in methods} != names:
            raise AssertionError('Batch-processing functions are missing.')
        namespace = {
            'Error': ProcessingError,
            'Logger': lambda: SimpleNamespace(write=lambda exception: None),
            'DataFrame': FakeDataFrame,
            'List': list,
            'json': json,
            'os': os,
            'pd': SimpleNamespace(DataFrame=FakeDataFrame),
        }
        module = ast.fix_missing_locations(ast.Module(
            body=[guard] + methods, type_ignores=[]))
        exec(compile(module, str(ROOT / 'processors.py'), 'exec'), namespace)
        cls.functions = namespace

    def setUp(self) -> None:
        """Create an identity cleaning pipeline with a working lemmatizer."""
        self.parser = SimpleNamespace(
            collapse_whitespace=lambda text: text,
            normalize_text=lambda text: text,
            remove_encodings=lambda text: text,
            remove_symbols=lambda text: text,
            remove_fragments=lambda text: text,
            remove_stopwords=lambda text: text,
            lemmatizer=SimpleNamespace(lemmatize=lambda token: token),
        )

    def test_chunk_datasets_writes_workbook_and_returns_rows(self) -> None:
        """Confirm the historical Data column and workbook side effect."""
        with TemporaryDirectory() as root:
            source = Path(root) / 'source'
            destination = Path(root) / 'destination'
            source.mkdir()
            destination.mkdir()
            (source / 'sample.txt').write_text('one two three four', encoding='utf-8')
            result = self.functions['chunk_datasets'](
                self.parser, str(source), str(destination), 2)
            self.assertEqual(['Data'], result.columns)
            self.assertEqual(['one two', 'three four'], result.records)
            self.assertEqual('one two\nthree four',
                             (destination / 'sample.xlsx').read_text(encoding='utf-8'))

    def test_json_lines_records_parse_individually(self) -> None:
        """Confirm every generated JSONL row parses as an independent JSON object."""
        with TemporaryDirectory() as root:
            source = Path(root) / 'source'
            destination = Path(root) / 'destination'
            source.mkdir()
            destination.mkdir()
            (source / 'sample.txt').write_text('one two three', encoding='utf-8')
            self.functions['convert_jsonl'](
                self.parser, str(source), str(destination), 2)
            lines = (destination / 'sample.jsonl').read_text(encoding='utf-8').splitlines()
            self.assertEqual([{'0': ['one', 'two']}, {'1': ['three']}],
                             [json.loads(line) for line in lines])

    def test_invalid_chunk_size_is_rejected(self) -> None:
        """Reject zero and noninteger chunk sizes before processing files."""
        with TemporaryDirectory() as root:
            for method in ('chunk_datasets', 'convert_jsonl'):
                for value in (0, -1, 1.5, True):
                    with self.subTest(method=method, size=value):
                        with self.assertRaises(ProcessingError):
                            self.functions[method](self.parser, root, root, value)


if __name__ == '__main__':
    unittest.main()
