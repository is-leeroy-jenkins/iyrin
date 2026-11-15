"""Regression tests for browser-first Geocoding input synchronization.

Purpose:
    Confirm delayed browser geolocation updates untouched input controls while
    manual edits, explicit clears, and existing mapping controls remain intact.
"""
from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Optional
import unittest


SOURCE_PATH = Path( __file__ ).resolve( ).parents[ 1 ] / 'app.py'
SOURCE = SOURCE_PATH.read_text( encoding='utf-8' )


class GeocodingBrowserDefaultTests( unittest.TestCase ):
    """Validate the Geocoding input's active-location synchronization.

    Attributes:
        state (dict): Isolated Streamlit session-state values.
        functions (dict): Application functions compiled from the actual app.py AST.
    """

    def setUp( self ) -> None:
        """Create isolated Streamlit state and load the real synchronization functions.

        Purpose:
            Exercise the application's functions without initializing unrelated
            Streamlit providers or requiring browser access.

        Returns:
            None: Initializes a fresh test environment.
        """
        self.state = { }
        names = { 'compose_location_from_state', 'get_global_location_default',
            'mark_geocoding_location_modified', 'sync_geocoding_location_input' }
        tree = ast.parse( SOURCE )
        functions = [ node for node in tree.body if isinstance( node, ast.FunctionDef )
            and node.name in names ]
        self.assertEqual( names, { node.name for node in functions } )
        module = ast.fix_missing_locations( ast.Module( body=functions, type_ignores=[ ] ) )
        self.functions = { 'st': SimpleNamespace( session_state=self.state ),
            'Optional': Optional }
        exec( compile( module, str( SOURCE_PATH ), 'exec' ), self.functions )

    def test_first_render_without_location_is_empty( self ) -> None:
        """Initialize an empty input while browser geolocation is pending."""
        self.functions[ 'sync_geocoding_location_input' ]( )
        self.assertEqual( '', self.state[ 'geocoding_location_input' ] )

    def test_delayed_browser_location_populates_existing_empty_input( self ) -> None:
        """Refresh an existing blank widget after browser reverse-geocoding succeeds."""
        self.functions[ 'sync_geocoding_location_input' ]( )
        self.state[ 'location' ] = 'Arlington, Virginia'
        self.functions[ 'sync_geocoding_location_input' ]( )
        self.assertEqual( 'Arlington, Virginia', self.state[ 'geocoding_location_input' ] )

    def test_coordinate_fallback_populates_input( self ) -> None:
        """Expose latitude and longitude text when reverse geocoding fails."""
        self.state[ 'location' ] = '38.881600, -77.091000'
        self.functions[ 'sync_geocoding_location_input' ]( )
        self.assertEqual( '38.881600, -77.091000',
            self.state[ 'geocoding_location_input' ] )

    def test_untouched_input_follows_global_location_updates( self ) -> None:
        """Refresh defaults when the canonical location changes before manual editing."""
        self.state[ 'location' ] = 'Arlington, Virginia'
        self.functions[ 'sync_geocoding_location_input' ]( )
        self.state[ 'location' ] = 'Alexandria, Virginia'
        self.functions[ 'sync_geocoding_location_input' ]( )
        self.assertEqual( 'Alexandria, Virginia', self.state[ 'geocoding_location_input' ] )

    def test_manual_entry_survives_browser_location_update( self ) -> None:
        """Never replace user-entered query text with subsequent browser values."""
        self.state[ 'geocoding_location_input' ] = 'Dumfries, Virginia'
        self.functions[ 'mark_geocoding_location_modified' ]( )
        self.state[ 'location' ] = 'Arlington, Virginia'
        self.functions[ 'sync_geocoding_location_input' ]( )
        self.assertEqual( 'Dumfries, Virginia', self.state[ 'geocoding_location_input' ] )

    def test_explicit_clear_survives_streamlit_rerun( self ) -> None:
        """Keep an intentionally cleared field empty even when browser state is valid."""
        self.state[ 'location' ] = 'Arlington, Virginia'
        self.state[ 'geocoding_location_input' ] = ''
        self.functions[ 'mark_geocoding_location_modified' ]( )
        self.functions[ 'sync_geocoding_location_input' ]( )
        self.assertEqual( '', self.state[ 'geocoding_location_input' ] )

    def test_ui_wiring_preserves_browser_error_visibility( self ) -> None:
        """Verify the existing widget exposes errors and tracks user modifications."""
        self.assertIn( "on_change=mark_geocoding_location_modified", SOURCE )
        self.assertIn( "st.warning( browser_error )", SOURCE )
        self.assertIn( "st.session_state[ 'clear_geocoding_location_input' ] = True", SOURCE )
        self.assertIn( "bootstrap_browser_geolocation( geocoder )", SOURCE )
        self.assertIn( "ensure_active_location_state( )", SOURCE )


if __name__ == '__main__':
    unittest.main( )
