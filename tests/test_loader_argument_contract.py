"""Regression tests for validated document-loader options and API arguments."""

import ast
import copy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock


ROOT = Path(__file__).resolve().parents[1]


class LoaderError(Exception):
    """Represent the application's logged exception wrapper."""


class LoaderArgumentContractTests(unittest.TestCase):
    """Verify existing loader aliases and strict argument validation."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load selected production methods without external loader SDKs."""
        tree = ast.parse((ROOT / 'loaders.py').read_text(encoding='utf-8'))
        target_names = {
            'PdfLoader': {'normalize_mode', 'normalize_extraction', 'normalize_image_format'},
            'ExcelLoader': {'normalize_mode'},
            'MarkdownLoader': {'normalize_mode'},
            'PowerPointLoader': {'normalize_mode'},
            'JsonLoader': {'load'},
        }
        guard = next(node for node in tree.body
                     if isinstance(node, ast.FunctionDef) and node.name == 'throw_if')
        functions = [guard]
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name in target_names:
                for method in node.body:
                    if isinstance(method, ast.FunctionDef) and method.name in target_names[node.name]:
                        definition = copy.deepcopy(method)
                        definition.name = f'{node.name}_{method.name}'
                        functions.append(definition)

        cls.loader_factory = MagicMock()
        namespace = {
            'Error': LoaderError,
            'Logger': lambda: SimpleNamespace(write=lambda exception: None),
            'JSONLoader': cls.loader_factory,
            'List': list,
            'Document': object,
            'Optional': __import__('typing').Optional,
        }
        module = ast.fix_missing_locations(ast.Module(body=functions, type_ignores=[]))
        exec(compile(module, str(ROOT / 'loaders.py'), 'exec'), namespace)
        cls.functions = namespace

    def setUp(self) -> None:
        """Reset provider mocks before each independent regression test."""
        self.loader_factory.reset_mock()

    def test_pdf_options_keep_supported_aliases(self) -> None:
        """Recognize documented aliases and reject unsupported settings."""
        pdf = SimpleNamespace(
            mode_options=['single', 'page'],
            extraction_options=['plain', 'layout'],
            image_options=['html-img', 'markdown-img', 'text-img'],
        )
        self.assertEqual('page', self.functions['PdfLoader_normalize_mode'](pdf, 'elements'))
        self.assertEqual('layout', self.functions['PdfLoader_normalize_extraction'](pdf, 'ocr'))
        self.assertEqual('markdown-img',
                         self.functions['PdfLoader_normalize_image_format'](pdf, 'text'))
        for method in ('normalize_mode', 'normalize_extraction', 'normalize_image_format'):
            with self.subTest(method=method):
                with self.assertRaises(LoaderError):
                    self.functions[f'PdfLoader_{method}'](pdf, 'unsupported')

    def test_other_loader_modes_keep_aliases(self) -> None:
        """Preserve aliases in Excel, Markdown, and PowerPoint loaders."""
        modes = [
            ('ExcelLoader', 'paged'),
            ('MarkdownLoader', 'page'),
            ('PowerPointLoader', 'multiple'),
        ]
        for provider, alias in modes:
            with self.subTest(provider=provider):
                target = SimpleNamespace(mode_options=['single', 'elements'])
                method = self.functions[f'{provider}_normalize_mode']
                self.assertEqual('elements', method(target, alias))
                with self.assertRaises(LoaderError):
                    method(target, None)

    def test_json_loader_rejects_implicit_boolean_conversion(self) -> None:
        """Reject invalid bool and schema inputs before calling JSONLoader."""
        target = SimpleNamespace(verify_exists=lambda path: path)
        loader = self.functions['JsonLoader_load']
        with self.assertRaises(LoaderError):
            loader(target, '/data.json', '.', None, 1, False)
        with self.assertRaises(LoaderError):
            loader(target, '/data.json', '', None, True, False)
        self.loader_factory.assert_not_called()

    def test_json_loader_keeps_valid_values(self) -> None:
        """Pass validated member values to the underlying JSON loader."""
        target = SimpleNamespace(verify_exists=lambda path: path)
        loader = self.functions['JsonLoader_load']
        self.assertEqual(self.loader_factory.return_value.load.return_value,
                         loader(target, '/data.json', '.', None, True, False))
        self.loader_factory.assert_called_once_with(
            file_path='/data.json', jq_schema='.',
            text_content=True, json_lines=False)


if __name__ == '__main__':
    unittest.main()
