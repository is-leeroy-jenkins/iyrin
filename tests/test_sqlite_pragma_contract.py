"""Regression coverage for SQLite read-only PRAGMA execution gate."""

import ast
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SQLitePragmaContractTests(unittest.TestCase):
    """Prevent mutation through SQLite PRAGMA statements."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load the SQL gate without importing provider storage SDKs."""
        tree = ast.parse((ROOT / 'storage.py').read_text(encoding='utf-8'))
        db = next(node for node in tree.body
                  if isinstance(node, ast.ClassDef) and node.name == 'SQLiteDatabase')
        fn = next(node for node in db.body
                  if isinstance(node, ast.FunctionDef) and node.name == 'is_safe_query')
        module = ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[]))
        namespace = {'re': re}
        exec(compile(module, str(ROOT / 'storage.py'), 'exec'), namespace)
        cls.gate = staticmethod(namespace['is_safe_query'])

    def test_read_only_pragma_metadata_allowed(self) -> None:
        """Allow ordinary SQLite metadata queries."""
        for query in ('PRAGMA table_info(test)', 'PRAGMA index_list("test")',
                      'PRAGMA database_list', 'PRAGMA main.table_xinfo(test)'):
            with self.subTest(query=query):
                self.assertTrue(self.gate(None, query))

    def test_mutating_pragma_forms_rejected(self) -> None:
        """Block setters and checkpoint operations, including parenthesized values."""
        for query in ('PRAGMA journal_mode=WAL',
                      'PRAGMA journal_mode(WAL)',
                      'PRAGMA wal_checkpoint(TRUNCATE)',
                      'PRAGMA foreign_keys=OFF',
                      'PRAGMA writable_schema=ON',
                      'PRAGMA optimize'):
            with self.subTest(query=query):
                self.assertFalse(self.gate(None, query))


if __name__ == '__main__':
    unittest.main()
