"""Regression checks for map and places cache-key method contracts."""

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import List
import unittest


ROOT = Path(__file__).resolve().parents[1]


class MappingError(Exception):
    """Represent a logged mapping exception."""


class MappingCacheContractTests(unittest.TestCase):
    """Ensure cache-key text remains stable after removing variadic arguments."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load the real Geocoder and Place cache-key methods."""
        tree = ast.parse((ROOT / 'mapping.py').read_text(encoding='utf-8'))
        names = ('Geocoder', 'Place')
        namespace = {
            'Error': MappingError,
            'Logger': lambda: SimpleNamespace(write=lambda exception: None),
            'List': List,
        }
        guard = next(node for node in tree.body
                     if isinstance(node, ast.FunctionDef) and node.name == 'throw_if')
        methods = [guard]
        for parent in tree.body:
            if isinstance(parent, ast.ClassDef) and parent.name in names:
                method = next(node for node in parent.body
                              if isinstance(node, ast.FunctionDef)
                              and node.name == 'key_for')
                import copy
                fn = copy.deepcopy(method)
                fn.name = f'{parent.name}_key_for'
                methods.append(fn)
        module = ast.fix_missing_locations(ast.Module(body=methods, type_ignores=[]))
        exec(compile(module, str(ROOT / 'mapping.py'), 'exec'), namespace)
        cls.functions = namespace

    def test_cache_keys_retain_prior_text(self) -> None:
        """Preserve the prefix and separated-part representation."""
        for kind in ('Geocoder', 'Place'):
            with self.subTest(kind=kind):
                obj = SimpleNamespace()
                key = self.functions[f'{kind}_key_for'](
                    obj, 'geocode', ['New York', 'US'])
                self.assertEqual('geocode::New York US', key)

    def test_bad_cache_part_arguments_are_rejected(self) -> None:
        """Reject scalar parts and missing prefixes."""
        for kind in ('Geocoder', 'Place'):
            fn = self.functions[f'{kind}_key_for']
            with self.assertRaises(MappingError):
                fn(SimpleNamespace(), 'geocode', 'New York')
            with self.assertRaises(MappingError):
                fn(SimpleNamespace(), None, ['US'])


if __name__ == '__main__':
    unittest.main()
