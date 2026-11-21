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
            OPENSKY_CLIENT_SECRET='configured-secret',
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
        initialize = load_live_world_function('initialize_world_state', namespace)
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
        initialize = load_live_world_function('initialize_world_state', namespace)
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


    def test_credential_registry_covers_configuration_inventory(self) -> None:
        """Every canonical OS-backed application credential has a sidebar definition."""
        tree = ast.parse((ROOT / 'config.py').read_text(encoding='utf-8'))
        registry_node = next(node for node in tree.body
            if isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == 'API_CREDENTIAL_FIELDS')
        fields = ast.literal_eval(registry_node.value)

        configured = set()
        for node in tree.body:
            if not isinstance(node, ast.Assign) or not node.targets:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue
            source = ast.get_source_segment(
                (ROOT / 'config.py').read_text(encoding='utf-8'), node) or ''
            if 'os.getenv(' in source and (
                '_API_KEY' in target.id or '_TOKEN' in target.id
                or '_SECRET' in target.id or '_CLIENT_ID' in target.id
                or target.id in ('FIRMS_MAP_KEY', 'GOOGLE_ACCOUNT_FILE',
                    'GOOGLE_CSE_ID', 'GOOGLE_CLOUD_PROJECT_ID',
                    'GOOGLE_CLOUD_LOCATION', 'GOOGLE_GENAI_USE_VERTEXAI',
                    'GOOGLE_DRIVE_TOKEN_PATH', 'GOOGLE_DRIVE_FOLDER_ID',
                    'CHROMA_TENET_ID', 'OPENSKY_CLIENT_ID', 'SKYMAP_TOKEN')
            ):
                configured.add(target.id)

        self.assertEqual(configured, set(fields))
        self.assertEqual(48, len(fields))
        self.assertEqual('OPENSKY_CLIENT_SECRET',
            fields['OPENSKY_CLIENT_SECRET'][1])
        self.assertEqual('NEWSAPI_API_KEY', fields['NEWS_API_KEY'][1])
        self.assertEqual('GOOGLE_ACCOUNT_CREDENTIALS',
            fields['GOOGLE_ACCOUNT_FILE'][1])

    def test_credential_editor_is_available_without_environment_gate(self) -> None:
        """The complete credentials form must be visible without an opt-in flag."""
        source = (ROOT / 'app.py').read_text(encoding='utf-8')
        self.assertNotIn('IYRIN_SINGLE_USER_MODE', source)
        self.assertIn("initialize_api_credential_state( )\n\nwith st.sidebar:", source)
        self.assertIn("with st.form( 'api_credentials_form'", source)
        self.assertIn("st.form_submit_button( 'Apply'", source)
        self.assertIn("st.form_submit_button( 'Reset to OS Defaults'", source)
        self.assertIn("get_opensky_service.clear( )", source)


if __name__ == '__main__':
    unittest.main()
