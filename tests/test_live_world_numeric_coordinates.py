"""Regress numeric coordinate handling from pandas-backed Live World rows."""

import ast
from fractions import Fraction
import math
from numbers import Real
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ToolError(Exception):
    """Represent the application's logged tool exception."""


class FakeEntityFrame:
    """Expose one pandas-like observation row for nearest-entity lookup."""

    empty = False

    def copy(self):
        """Return the existing frame without changing its observations."""
        return self

    def iterrows(self):
        """Yield one valid numeric observation from a DataFrame."""
        return [(0, {'Latitude': Fraction(38), 'Longitude': Fraction(-77),
                     'EntityType': 'Aircraft'})]


class LiveWorldNumericCoordinateTests(unittest.TestCase):
    """Validate numeric scalar acceptance without string coercion."""

    @classmethod
    def setUpClass(cls) -> None:
        """Compile the actual distance and nearest-entity functions."""
        tree = ast.parse((ROOT / 'tools.py').read_text(encoding='utf-8'))
        names = {'throw_if', 'calculate_distance_nm',
                 'calculate_bearing', 'find_live_world_nearest'}
        functions = [node for node in tree.body
                     if isinstance(node, ast.FunctionDef) and node.name in names]
        if {node.name for node in functions} != names:
            raise AssertionError('Required geographic functions are missing.')
        namespace = {
            'Dict': Dict, 'List': List,
            'math': math, 'Real': Real,
            'Error': ToolError,
            'Logger': lambda: SimpleNamespace(write=lambda exception: None),
            'LIVE_WORLD_ENTITY_TYPES': ['Aircraft'],
            'st': SimpleNamespace(session_state={
                'live_world_df_entities': FakeEntityFrame()}),
            'pd': SimpleNamespace(DataFrame=FakeEntityFrame),
            'make_entity_record': lambda row: dict(row),
        }
        module = ast.fix_missing_locations(ast.Module(body=functions, type_ignores=[]))
        exec(compile(module, str(ROOT / 'tools.py'), 'exec'), namespace)
        cls.functions = namespace

    def test_real_numeric_scalars_are_supported(self) -> None:
        """Accept Real-valued observations without requiring built-in float types."""
        distance = self.functions['calculate_distance_nm'](
            Fraction(38), Fraction(-77), Fraction(38), Fraction(-77))
        self.assertAlmostEqual(0.0, distance)
        records = self.functions['find_live_world_nearest'](
            38.0, -77.0, 5.0, 'All', 10)
        self.assertEqual(1, len(records))
        self.assertAlmostEqual(0.0, records[0]['DistanceNM'])

    def test_boolean_and_string_coordinates_are_rejected(self) -> None:
        """Reject non-coordinate values instead of silently converting them."""
        with self.assertRaises(ToolError):
            self.functions['calculate_distance_nm'](
                True, -77.0, 38.0, -77.0)
        with self.assertRaises(ToolError):
            self.functions['calculate_bearing'](
                '38', -77.0, 38.0, -77.0)


if __name__ == '__main__':
    unittest.main()
