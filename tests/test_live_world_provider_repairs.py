"""Regression coverage for Live World provider contracts and diagnostic integrity."""

from __future__ import annotations

import ast
from pathlib import Path
import re
import sys
import traceback
from typing import Any
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_function( path: str, name: str, namespace: dict[str, Any] ) -> Any:
    """Compile one repository function with controlled dependencies.

    Purpose:
        Execute production helper functions in isolation without external network calls.

    Args:
        path (str): Repository-relative source path.
        name (str): Top-level function to compile.
        namespace (dict[str, Any]): Functions and modules required at runtime.

    Returns:
        Any: The compiled callable.
    """
    source = (ROOT / path).read_text( encoding='utf-8' )
    tree = ast.parse( source )
    functions = [ node for node in tree.body if isinstance( node, ast.FunctionDef ) ]
    if path == 'realtime.py':
        functions.extend( method for cls in tree.body if isinstance( cls, ast.ClassDef )
            for method in cls.body if isinstance( method, ast.FunctionDef ) )
    function = next( node for node in functions if node.name == name )
    function.decorator_list = []
    module = ast.fix_missing_locations( ast.Module( body=[ function ], type_ignores=[ ] ) )
    exec( compile( module, str( ROOT / path ), 'exec' ), namespace )
    return namespace[ name ]


class LiveWorldProviderRepairsTests( unittest.TestCase ):
    """Verify the Live World configuration, validation, and exception contracts.

    Attributes:
        root (Path): Root of the repository containing the application modules.
    """

    root: Path = ROOT

    def test_opensky_credentials_are_owned_by_provider_configuration( self ) -> None:
        """Ensure OpenSky credentials are not propagated through the Streamlit UI."""
        app = (self.root / 'app.py').read_text( encoding='utf-8' )
        realtime = (self.root / 'realtime.py').read_text( encoding='utf-8' )
        sources = (self.root / 'sources.py').read_text( encoding='utf-8' )
        config = (self.root / 'config.py').read_text( encoding='utf-8' )
        self.assertIn( 'self.client_id = cfg.OPENSKY_CLIENT_ID', sources )
        self.assertIn( 'self.client_secret = cfg.OPENSKY_API_CLIENT_SECRET', sources )
        self.assertIn( 'OpenSkyLive( timeout=20 )', realtime )
        self.assertNotIn( "st.session_state.get( 'opensky_api_credentials', '' )", realtime )
        self.assertNotIn( 'st.session_state.opensky_api_credentials', app )
        self.assertIn( "OPENSKY_CLIENT_ID = os.getenv(", config )
        self.assertIn( "OPENSKY_API_CLIENT_SECRET = os.getenv(", config )

    def test_long_exception_keeps_diagnostics_without_exposing_secrets( self ) -> None:
        """Retain verbose exception messages without losing secret redaction."""
        namespace: dict[str, Any] = {
            're': re,
            'get_config_bool': lambda name, default=False: False,
        }
        sanitize = load_function( 'boogr.py', 'sanitize_text', namespace )
        message = 'Provider request failed: ' + ', '.join(
            f'field_{index}' for index in range( 50 ) )
        self.assertEqual( '[MANIFEST_ROW]', sanitize( message ) )
        self.assertEqual( message, sanitize( message, 2000, mask_payload=False ) )
        self.assertEqual( 'token=[SECRET]',
            sanitize( 'token=super-private', mask_payload=False ) )

    def test_coordinates_must_be_finite_and_in_range( self ) -> None:
        """Reject invalid positions without silently modifying valid coordinates."""
        import math

        namespace: dict[str, Any] = { 'math': math }
        validate = load_function(
            'realtime.py', 'is_valid_live_world_coordinates', namespace )
        self.assertTrue( validate( 38.8951, -77.0364 ) )
        self.assertTrue( validate( 0.0, 0.0 ) )
        self.assertFalse( validate( math.nan, -77.0 ) )
        self.assertFalse( validate( 38.0, math.inf ) )
        self.assertFalse( validate( 91.0, 0.0 ) )
        self.assertFalse( validate( 0.0, -181.0 ) )
        self.assertFalse( validate( True, 0.0 ) )

    def test_replay_is_not_gated_on_live_entities( self ) -> None:
        """Verify that historical mode bypasses the live-entities early return."""
        source = (self.root / 'realtime.py').read_text( encoding='utf-8' )
        self.assertIn(
            "or self.state[ 'live_world_historical_replay' ]", source )
        self.assertIn( "live_world_refresh_id", source )
        self.assertIn( "live_world_last_success", source )

    def test_overpass_classifiers_skip_empty_tag_mappings( self ) -> None:
        """Verify all three classifiers treat untagged features as unclassified."""
        tree = ast.parse( (self.root / 'sources.py').read_text( encoding='utf-8' ) )
        for class_name, method_name in [
            ( 'OverpassInfrastructure', 'classify_infrastructure' ),
            ( 'OverpassCameras', 'classify_camera' ),
            ( 'OverpassMapLayers', 'classify_feature' ),
        ]:
            cls = next( node for node in tree.body
                if isinstance( node, ast.ClassDef ) and node.name == class_name )
            method = next( node for node in cls.body
                if isinstance( node, ast.FunctionDef ) and node.name == method_name )
            namespace: dict[str, Any] = { 'Dict': dict, 'Any': Any,
                'Error': RuntimeError,
                'Logger': lambda: type( 'Recorder', (), { 'write': lambda self, ex: None } )( ) }
            module = ast.fix_missing_locations(
                ast.Module( body=[ method ], type_ignores=[ ] ) )
            exec( compile( module, class_name, 'exec' ), namespace )
            classifier = namespace[ method_name ]
            self.assertEqual( '', classifier( object( ), { } ) )

    def test_opensky_payload_shape_is_checked( self ) -> None:
        """Verify a malformed provider envelope fails before entity parsing."""
        source = (self.root / 'sources.py').read_text( encoding='utf-8' )
        self.assertIn( 'OpenSky states response must be a dictionary.', source )
        self.assertIn( 'OpenSky states must be a list or null.', source )


if __name__ == '__main__':
    unittest.main()
