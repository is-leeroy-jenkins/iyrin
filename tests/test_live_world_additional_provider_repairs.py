"""Regression tests for FIRMS CSV and camera classification contracts.

Purpose:
    Keep public source parsing deterministic and reject malformed provider responses
    without live network calls.
"""
from __future__ import annotations

import ast
import io
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List
import unittest

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


class SourceFailure(Exception):
    """Represent the application's wrapped provider exception."""


class LiveWorldAdditionalProviderTests(unittest.TestCase):
    """Verify FIRMS response handling and OpenStreetMap camera classification."""

    def load_method(self, path: str, class_name: str, method_name: str) -> Any:
        """Compile one production class method using mockable external references.

        Args:
            path (str): Repository-relative Python module.
            class_name (str): Source class name.
            method_name (str): Method to compile.

        Returns:
            Any: Unbound production method.
        """
        tree = ast.parse((ROOT / path).read_text(encoding='utf-8'))
        cls = next(node for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == class_name)
        method = next(node for node in cls.body
            if isinstance(node, ast.FunctionDef) and node.name == method_name)
        namespace: Dict[str, Any] = {
            'pd': pd,
            'io': io,
            'Any': Any,
            'Dict': Dict,
            'List': List,
            'Error': SourceFailure,
            'throw_if': lambda name, value: None,
            'Logger': lambda: SimpleNamespace(write=lambda exception: None),
        }
        module = ast.fix_missing_locations(ast.Module(
            body=[method], type_ignores=[]))
        exec(compile(module, path, 'exec'), namespace)
        return namespace[method_name]

    def test_firms_header_only_is_valid_empty_result(self) -> None:
        """Accept an empty but correctly formatted NASA FIRMS CSV response."""
        parse = self.load_method('fetchers.py', 'Firms', 'csv_to_rows')
        service = SimpleNamespace()
        rows = parse(service, 'latitude,longitude,acq_date\n')
        self.assertEqual([], rows)

    def test_firms_unexpected_schema_is_rejected(self) -> None:
        """Do not count an unrelated HTTP-successful CSV as FIRMS detections."""
        parse = self.load_method('fetchers.py', 'Firms', 'csv_to_rows')
        service = SimpleNamespace()
        with self.assertRaises(SourceFailure):
            parse(service, 'message,status\nserver error,200\n')

    def test_firms_nonempty_unparsable_response_is_rejected(self) -> None:
        """An HTTP-successful provider message without CSV columns is not zero fires."""
        parse = self.load_method('fetchers.py', 'Firms', 'csv_to_rows')
        service = SimpleNamespace()
        with self.assertRaises(SourceFailure):
            parse(service, ';;;')

    def test_camera_guard_is_not_treated_as_cctv(self) -> None:
        """A surveillance tag alone doesn't prove the existence of a camera."""
        classify = self.load_method('sources.py', 'OverpassCameras', 'classify_camera')
        self.assertEqual('', classify(SimpleNamespace(), {
            'man_made': 'surveillance', 'surveillance:type': 'guard',
        }))

    def test_camera_explicit_camera_type_is_retained(self) -> None:
        """Keep camera entities with an explicit OSM camera classification."""
        classify = self.load_method('sources.py', 'OverpassCameras', 'classify_camera')
        self.assertEqual('CCTV / Surveillance', classify(SimpleNamespace(), {
            'man_made': 'surveillance', 'surveillance:type': 'camera',
        }))

    def test_camera_existing_empty_webcam_key_is_classified(self) -> None:
        """Classify the OSM webcam key using the same existence rule as Overpass."""
        classify = self.load_method('sources.py', 'OverpassCameras', 'classify_camera')
        category = classify(SimpleNamespace(), {'webcam': ''})
        self.assertEqual('Web Cameras', category)


if __name__ == '__main__':
    unittest.main()
