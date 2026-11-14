"""Regression tests for geocode enrichment when providers return empty results."""

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, Optional
import unittest
from unittest.mock import MagicMock


ROOT = Path( __file__ ).resolve( ).parents[ 1 ]


def load_excel_resolution_methods( ):
    """Load production resolution methods without requiring external Google SDKs."""
    tree = ast.parse( (ROOT / 'excel.py').read_text( encoding='utf-8' ) )
    cls = next( node for node in tree.body
        if isinstance( node, ast.ClassDef ) and node.name == 'Excel' )
    names = { 'resolve_address', 'resolve_city_state_country' }
    methods = [ node for node in cls.body
        if isinstance( node, ast.FunctionDef ) and node.name in names ]
    if { node.name for node in methods } != names:
        raise RuntimeError( 'Excel resolution methods are missing.' )
    guard = next( node for node in tree.body
        if isinstance( node, ast.FunctionDef ) and node.name == 'throw_if' )
    isolated_class = ast.ClassDef( name='Excel', bases=[ ], keywords=[ ],
        body=methods, decorator_list=[ ] )
    module = ast.Module( body=[ guard, isolated_class ], type_ignores=[ ] )
    environment = { 'Optional': Optional, 'Dict': Dict,
        'Error': lambda error: error, 'Logger': MagicMock( ) }
    exec( compile( ast.fix_missing_locations( module ), '<excel>', 'exec' ),
        environment )
    return environment[ 'Excel' ]


Excel = load_excel_resolution_methods( )


class ExcelResolutionTests( unittest.TestCase ):
    """Verify empty results fall through to the next resolver."""

    def create_excel( self, geocode_result, place_result ):
        """Create a provider-independent Excel resolver."""
        excel = Excel( )
        excel.geocoder = SimpleNamespace(
            freeform=MagicMock( return_value=geocode_result ),
            city_state_country=MagicMock( return_value=geocode_result ) )
        excel.places = SimpleNamespace(
            text_to_location=MagicMock( return_value=place_result ) )
        return excel

    def test_address_empty_geocoder_uses_places( self ) -> None:
        """Fall back to Places when a freeform geocoder returns no result."""
        excel = self.create_excel( { }, { 'lat': 38.9 } )
        result = excel.resolve_address( 'Arlington, VA' )
        self.assertEqual( 'ok_places', result[ 'status' ] )
        excel.places.text_to_location.assert_called_once( )

    def test_address_both_empty_are_not_found( self ) -> None:
        """Report not_found when both address providers return empty results."""
        excel = self.create_excel( { }, None )
        result = excel.resolve_address( 'Unrecognized place' )
        self.assertEqual( 'not_found', result[ 'status' ] )
        self.assertEqual( { }, result[ 'result' ] )

    def test_address_geocoder_success_skips_places( self ) -> None:
        """Avoid unnecessary Places calls after geocoding succeeds."""
        excel = self.create_excel( { 'lat': 38.9 }, { 'lat': 39.0 } )
        result = excel.resolve_address( 'Arlington, VA' )
        self.assertEqual( 'ok', result[ 'status' ] )
        excel.places.text_to_location.assert_not_called( )

    def test_city_empty_geocoder_uses_places( self ) -> None:
        """Resolve structured addresses through Places when geocoding is empty."""
        excel = self.create_excel( None, { 'lat': 38.9 } )
        result = excel.resolve_city_state_country( 'Arlington', 'VA', 'US' )
        self.assertEqual( 'ok_places', result[ 'status' ] )

    def test_city_both_empty_are_not_found( self ) -> None:
        """Retain not_found for a structured location with no provider match."""
        excel = self.create_excel( { }, { } )
        result = excel.resolve_city_state_country( 'Missing', '', 'US' )
        self.assertEqual( 'not_found', result[ 'status' ] )

    def test_provider_exceptions_preserve_not_found( self ) -> None:
        """Return combined provider errors without false-positive success."""
        excel = self.create_excel( None, None )
        excel.geocoder.freeform.side_effect = RuntimeError( 'geocoding unavailable' )
        excel.places.text_to_location.side_effect = RuntimeError( 'places unavailable' )
        result = excel.resolve_address( 'Arlington, VA' )
        self.assertEqual( 'not_found', result[ 'status' ] )
        self.assertIn( 'geocoding unavailable', result[ 'error' ] )
        self.assertIn( 'places unavailable', result[ 'error' ] )


if __name__ == '__main__':
    unittest.main( )
