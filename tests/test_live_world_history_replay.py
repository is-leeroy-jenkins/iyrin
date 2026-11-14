"""Regression tests for historical replay's snapshot-relative UTC cutoff."""

import ast
from contextlib import nullcontext
import datetime as dt
from pathlib import Path
from types import SimpleNamespace
from typing import List
import unittest
from unittest.mock import MagicMock


ROOT = Path(__file__).resolve().parents[1]


class HistoryError(Exception):
    """Represent the application's logged history exception."""


class EmptyFrame:
    """Represent an empty historical replay result."""

    empty = True

    def __init__(self, columns: list[str] = []) -> None:
        """Capture optional column names for the empty-result contract."""
        self.columns = columns


class LiveWorldHistoryReplayTests(unittest.TestCase):
    """Verify snapshot-relative history selection and empty filters."""

    def setUp(self) -> None:
        """Compile the actual replay function against controlled persistence stubs."""
        tree = ast.parse((ROOT / 'history.py').read_text(encoding='utf-8'))
        names = {'throw_if', 'load_live_world_history'}
        methods = [node for node in tree.body
                   if isinstance(node, ast.FunctionDef) and node.name in names]
        self.assertEqual(names, {node.name for node in methods})
        self.reader = MagicMock(return_value=EmptyFrame())
        self.initialize = MagicMock()
        self.columns = ['ObservedAt']
        namespace = {
            'dt': dt,
            'List': List,
            'Error': HistoryError,
            'Logger': lambda: SimpleNamespace(write=lambda exception: None),
            'json': __import__('json'),
            'HISTORY_COLUMNS': self.columns,
            'HISTORY_TABLE': 'LiveWorldHistory',
            'cfg': SimpleNamespace(DB_PATH=':memory:'),
            'initialize_live_world_history': self.initialize,
            'sqlite3': SimpleNamespace(connect=lambda path: nullcontext(object())),
            'pd': SimpleNamespace(DataFrame=EmptyFrame, read_sql_query=self.reader),
        }
        module = ast.fix_missing_locations(ast.Module(body=methods, type_ignores=[]))
        exec(compile(module, str(ROOT / 'history.py'), 'exec'), namespace)
        self.load = namespace['load_live_world_history']

    def test_replay_cutoff_uses_selected_snapshot(self) -> None:
        """Use the replay snapshot, not the current wall-clock time."""
        self.load(4, ['aircraft'], '2025-01-02T00:00:00+00:00', 100)
        params = self.reader.call_args.kwargs['params']
        self.assertEqual('2025-01-02T00:00:00+00:00', params[1])
        self.assertEqual('2025-01-01T20:00:00+00:00', params[2])
        self.assertEqual(100, params[3])

    def test_empty_entity_types_skip_database_access(self) -> None:
        """Return a correctly shaped empty frame for an empty type filter."""
        result = self.load(4, [], '2025-01-02T00:00:00+00:00')
        self.assertEqual(self.columns, result.columns)
        self.reader.assert_not_called()
        self.initialize.assert_not_called()

    def test_invalid_snapshot_is_rejected(self) -> None:
        """Reject a naive timestamp rather than silently assuming UTC."""
        with self.assertRaises(HistoryError):
            self.load(4, ['aircraft'], '2025-01-02T00:00:00')


if __name__ == '__main__':
    unittest.main()
