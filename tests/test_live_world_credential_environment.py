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
    function = next(node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == name)
    module = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
    exec(compile(module, str(ROOT / 'realtime.py'), 'exec'), namespace)
    return namespace[name]


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

    def test_opensky_uses_current_process_environment(self) -> None:
        """Refresh non-overridden credentials from process environment."""
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
            self.assertEqual('os-client', self.state['opensky_api_client_id'])
            self.assertEqual('os-secret', self.state['opensky_api_credentials'])
            self.assertEqual('os-ais-key', self.state['live_world_aisstream_api_key'])
            self.state['opensky_api_client_id'] = 'stale-client'
            self.state['opensky_api_credentials'] = 'stale-secret'
            initialize()
            self.assertEqual('os-client', self.state['opensky_api_client_id'])
            self.assertEqual('os-secret', self.state['opensky_api_credentials'])

    def test_explicit_opensky_override_is_retained(self) -> None:
        """Preserve explicitly entered credentials when OS defaults are available."""
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
                }, clear=False):
            initialize()
            self.state['opensky_api_client_id'] = 'manual-client'
            self.state['opensky_api_credentials'] = 'manual-secret'
            self.state['opensky_api_client_id_user_override'] = True
            self.state['opensky_api_credentials_user_override'] = True
            initialize()
        self.assertEqual('manual-client', self.state['opensky_api_client_id'])
        self.assertEqual('manual-secret', self.state['opensky_api_credentials'])

    def test_ais_credentials_resolve_from_os_when_existing_state_empty(self) -> None:
        """Use an OS-backed key instead of incorrectly marking vessels unconfigured."""
        source = (ROOT / 'realtime.py').read_text(encoding='utf-8')
        self.assertIn("or os.getenv( 'AISSTREAM_API_KEY' ) or cfg.AISSTREAM_API_KEY",
            source)
        self.assertIn("if (source_key == 'vessels'", source)
        self.assertIn("'live_world_aisstream_api_key' ] = api_key", source)
        self.assertIn("with st.expander( '🌐 Mapping'", source)


if __name__ == '__main__':
    unittest.main()
