"""Regression tests for corrected provider argument guards and optional request data.

Purpose:
    Exercise source methods without importing optional cloud provider SDKs.
"""

import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock


ROOT = Path(__file__).resolve().parents[1]


class ProviderError(Exception):
    """Represent the application's logged provider exception wrapper."""


class ProviderArgumentContractTests(unittest.TestCase):
    """Verify argument contracts introduced by the fetcher remediation."""

    def setUp(self) -> None:
        """Load the production methods and their actual input guard."""
        source = (ROOT / 'fetchers.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        guard = next(node for node in tree.body
                     if isinstance(node, ast.FunctionDef) and node.name == 'throw_if')
        names = {
            'OpenScience': {'validate_format'},
            'GovData': {'validate_sort_field', 'validate_sort_order'},
            'AstroCatalog': {'request'},
        }
        methods = {}
        for cls in tree.body:
            if isinstance(cls, ast.ClassDef) and cls.name in names:
                for method in cls.body:
                    if isinstance(method, ast.FunctionDef) and method.name in names[cls.name]:
                        methods[(cls.name, method.name)] = method

        self.assertEqual(4, len(methods))
        module = ast.fix_missing_locations(ast.Module(
            body=[guard] + list(methods.values()), type_ignores=[]))

        self.http = MagicMock()
        self.http.get.return_value.headers = {'Content-Type': 'application/json'}
        self.http.get.return_value.json.return_value = {'ok': True}
        self.functions = {}
        namespace = {
            'Error': ProviderError,
            'Logger': lambda: SimpleNamespace(write=lambda exception: None),
            'requests': self.http,
            'Dict': dict,
            'Any': object,
            'Optional': __import__('typing').Optional,
        }
        exec(compile(module, str(ROOT / 'fetchers.py'), 'exec'), namespace)
        self.functions = namespace

    def test_validate_format_rejects_invalid_inputs(self) -> None:
        """Reject blank, missing, and non-string NASA output formats."""
        validator = self.functions['validate_format']
        target = SimpleNamespace()
        self.assertEqual('json', validator(target, 'JSON'))
        for value in (None, '', 7, 'invalid'):
            with self.subTest(value=value), self.assertRaises(ProviderError):
                validator(target, value)

    def test_sort_field_and_order_reject_silent_fallbacks(self) -> None:
        """Reject invalid sort values and preserve documented selections."""
        target = SimpleNamespace()
        field = self.functions['validate_sort_field']
        order = self.functions['validate_sort_order']
        self.assertEqual('lastModified', field(target, 'lastModified'))
        self.assertEqual('ASC', order(target, 'asc'))
        for value in (None, '', 12):
            with self.subTest(value=value):
                with self.assertRaises(ProviderError):
                    field(target, value)
                with self.assertRaises(ProviderError):
                    order(target, value)

    def test_optional_request_parameters_are_accepted(self) -> None:
        """Permit omitted query dictionaries while rejecting invalid argument types."""
        target = SimpleNamespace(base_url='https://example.org', headers={})
        request = self.functions['request']
        self.assertEqual({'ok': True}, request(target, 'items', None, 20))
        self.http.get.assert_called_once_with(
            url='https://example.org/items', params={},
            headers={}, timeout=20)
        with self.assertRaises(ProviderError):
            request(target, 'items', 'incorrect', 20)
        with self.assertRaises(ProviderError):
            request(target, 'items', None, 0)


if __name__ == '__main__':
    unittest.main()
