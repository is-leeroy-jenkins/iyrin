"""Regression tests for Live World OS credentials and Streamlit session state.

Purpose:
    Verify OS-backed credentials are resolved without overriding explicit settings
    or writing to keyed Streamlit widgets after their construction.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict
from unittest.mock import patch
import unittest

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def load_live_world_function(name: str, namespace: Dict[str, Any]) -> Any:
    """Load a single production Live World function with controlled dependencies.

    Purpose:
        Test real initialization behavior without importing application UI modules.

    Args:
        name (str): Function name from realtime.py.
        namespace (Dict[str, Any]): Required globals and simulated session state.

    Returns:
        Any: Function compiled from the repository source.
    """
    tree = ast.parse((ROOT / 'realtime.py').read_text(encoding='utf-8'))
    function = next(method for cls in tree.body if isinstance(cls, ast.ClassDef)
        for method in cls.body if isinstance(method, ast.FunctionDef)
        and method.name == name)
    function.decorator_list = []
    module = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
    exec(compile(module, str(ROOT / 'realtime.py'), 'exec'), namespace)
    service = SimpleNamespace(state=namespace['st'].session_state)
    return lambda: namespace[name](service)


class LiveWorldCredentialResolutionTests(unittest.TestCase):
    """Verify credential precedence and existing Live World state contracts.

    Attributes:
        state (Dict[str, Any]): Controlled Streamlit session values.
        config (SimpleNamespace): Mocked configuration defaults.
    """

    def setUp(self) -> None:
        """Create a clean state and configuration fixture."""
        self.state: Dict[str, Any] = {}
        self.config = SimpleNamespace(
            OPENSKY_CLIENT_ID='configured-client',
            OPENSKY_API_CREDENTIALS='configured-secret',
            AISSTREAM_API_KEY='configured-ais-key',
        )

    def test_initialize_preserves_unrelated_state_without_credentials(self) -> None:
        """Live World initialization must not copy API secrets into session state."""
        namespace: Dict[str, Any] = {
            'Dict': Dict,
            'pd': pd,
            'st': SimpleNamespace(session_state=self.state),
            'os': os,
            'cfg': self.config,
            'LIVE_WORLD_DATA_SOURCES': {},
        }
        initialize = load_live_world_function('initialize_live_world_state', namespace)
        with patch.dict(os.environ, {
                'OPENSKY_CLIENT_ID': 'os-client',
                'OPENSKY_API_CLIENT_SECRET': 'os-secret',
                'AISSTREAM_API_KEY': 'os-ais-key',
                }, clear=False):
            initialize()
            self.assertNotIn('opensky_api_client_id', self.state)
            self.assertNotIn('opensky_api_credentials', self.state)
            self.assertNotIn('live_world_aisstream_api_key', self.state)
            self.assertIn('live_world_df_aircraft', self.state)
            self.assertIn('live_world_df_vessels', self.state)

    def test_existing_live_world_state_is_not_overwritten(self) -> None:
        """The credential correction must not reset independent source settings."""
        namespace: Dict[str, Any] = {
            'Dict': Dict,
            'pd': pd,
            'st': SimpleNamespace(session_state=self.state),
            'os': os,
            'cfg': self.config,
            'LIVE_WORLD_DATA_SOURCES': {},
        }
        initialize = load_live_world_function('initialize_live_world_state', namespace)
        self.state['live_world_vessel_radius'] = 5.0
        initialize()
        self.assertEqual(5.0, self.state['live_world_vessel_radius'])

    def test_ais_uses_configuration_not_session_override(self) -> None:
        """The vessel fetcher must instantiate its cfg-backed provider without an API key."""
        source = (ROOT / 'realtime.py').read_text(encoding='utf-8')
        provider = (ROOT / 'sources.py').read_text(encoding='utf-8')
        self.assertIn("if source_key == 'vessels' and not cfg.AISSTREAM_API_KEY:", source)
        self.assertIn('AisStreamLive( timeout=5 )', source)
        self.assertIn('self.api_key = cfg.AISSTREAM_API_KEY', provider)
        self.assertNotIn("'live_world_aisstream_api_key' ] = api_key", source)


if __name__ == '__main__':
    unittest.main()
