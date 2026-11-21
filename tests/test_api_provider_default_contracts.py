"""Regression tests for documented API defaults and geographic request boundaries.

Purpose:
    Validate production request construction without issuing live API requests.
"""
from __future__ import annotations

import ast
import json
import math
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List
import unittest
from unittest.mock import Mock

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


class ProviderError(Exception):
    """Represent a wrapped API provider exception."""


def load_production_functions(path: str, class_name: str,
        method_names: List[str]) -> Dict[str, Any]:
    """Compile the specified real provider functions for isolated behavioral tests.

    Args:
        path (str): Repository-relative source file.
        class_name (str): Provider class, or empty string for module functions.
        method_names (List[str]): Production functions to load.

    Returns:
        Dict[str, Any]: Names and compiled production functions.
    """
    tree = ast.parse((ROOT / path).read_text(encoding='utf-8'))
    nodes = tree.body
    if class_name:
        cls = next(node for node in nodes
            if isinstance(node, ast.ClassDef) and node.name == class_name)
        nodes = cls.body
    functions = [node for node in nodes
        if isinstance(node, ast.FunctionDef) and node.name in method_names]
    namespace: Dict[str, Any] = {
        'Any': Any, 'Dict': Dict, 'List': List, 'math': math,
        'throw_if': lambda name, value: None,
        'Error': ProviderError,
        'Logger': lambda: SimpleNamespace(write=lambda exception: None),
    }
    module = ast.fix_missing_locations(ast.Module(body=functions, type_ignores=[]))
    exec(compile(module, path, 'exec'), namespace)
    return namespace


class ApiDefaultContractTests(unittest.TestCase):
    """Cover the request defaults verified against authoritative provider docs."""

    def test_firms_default_source_is_a_published_area_sensor(self) -> None:
        """The default Area-mode dispatcher must not omit NASA's required SOURCE."""
        tree = ast.parse((ROOT / 'fetchers.py').read_text(encoding='utf-8'))
        cls = next(node for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == 'Firms')
        method = next(node for node in cls.body
            if isinstance(node, ast.FunctionDef) and node.name == 'fetch')
        index = [argument.arg for argument in method.args.args].index('source')
        first_default = len(method.args.args) - len(method.args.defaults)
        default = ast.literal_eval(method.args.defaults[index - first_default])
        self.assertEqual('VIIRS_NOAA21_NRT', default)

    def test_firms_bounds_split_at_positive_antimeridian(self) -> None:
        """Use west,south,east,north rectangles within valid NASA FIRMS limits."""
        funcs = load_production_functions('realtime.py', '', [
            'create_world_bounding_box', 'create_world_bounding_boxes'])
        bounds = funcs['create_world_bounding_boxes'](10.0, 179.0)
        self.assertEqual([
            '177.000000,8.000000,180.000000,12.000000',
            '-180.000000,8.000000,-179.000000,12.000000',
        ], bounds)

    def test_firms_bounds_split_at_negative_antimeridian(self) -> None:
        """Split westbound coverage instead of clipping the other hemisphere."""
        funcs = load_production_functions('realtime.py', '', [
            'create_world_bounding_box', 'create_world_bounding_boxes'])
        bounds = funcs['create_world_bounding_boxes'](10.0, -179.0)
        self.assertEqual([
            '179.000000,8.000000,180.000000,12.000000',
            '-180.000000,8.000000,-177.000000,12.000000',
        ], bounds)

    def test_opensky_antimeridian_fetches_two_valid_bounding_boxes(self) -> None:
        """OpenSky requires all four bbox fields within WGS84 range."""
        funcs = load_production_functions('sources.py', 'OpenSkyLive', ['fetch_states'])
        calls: List[Dict[str, Any]] = []

        def fake_request(url: str, params: Dict[str, Any],
                headers: Dict[str, str], timeout: int) -> Any:
            """Record outgoing requests while returning one provider state vector."""
            calls.append(dict(params))
            response = Mock()
            response.json.return_value = {'time': 1, 'states': [
                ['abc123', 'CALL', '', '', '', 179.5, 10.0],
            ]}
            return response

        funcs['fetch_states'].__globals__['requests'] = SimpleNamespace(
            get=fake_request)
        source = SimpleNamespace(request_lock=nullcontext(), timeout=5,
            states_url='https://opensky-network.org/api/states/all',
            get_access_token=lambda: '')
        result = funcs['fetch_states'](source, 10.0, 179.0, 2.0)
        self.assertEqual(2, len(calls))
        self.assertEqual([177.0, -180.0], [x['lomin'] for x in calls])
        self.assertEqual([180.0, -179.0], [x['lomax'] for x in calls])
        self.assertEqual(1, len(result['states']))

    def test_nhats_defaults_use_documented_integer_enum_values(self) -> None:
        """JPL NHATS dv, dur, stay, launch, h and occ must be valid enums."""
        tree = ast.parse((ROOT / 'fetchers.py').read_text(encoding='utf-8'))
        cls = next(node for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == 'NearbyObjects')
        for method_name in ('fetch_nhats_summary', 'fetch_nhats_object', 'fetch'):
            method = next(node for node in cls.body
                if isinstance(node, ast.FunctionDef) and node.name == method_name)
            arguments = [argument.arg for argument in method.args.args]
            default_start = len(arguments) - len(method.args.defaults)
            defaults = {arguments[default_start + idx]: ast.literal_eval(value)
                for idx, value in enumerate(method.args.defaults)}
            self.assertEqual(6, defaults['dv'])
            self.assertIs(type(defaults['dv']), int)
            self.assertEqual(360, defaults['dur'])
            self.assertEqual(8, defaults['stay'])
            self.assertEqual('2020-2045', defaults['launch'])
            if method_name != 'fetch_nhats_object':
                self.assertEqual(26, defaults['h'])
                self.assertIs(type(defaults['h']), int)


if __name__ == '__main__':
    unittest.main()
