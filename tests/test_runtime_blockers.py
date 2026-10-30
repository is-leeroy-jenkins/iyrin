'''Regression checks for Excel credential wiring and Aggregate mode guards.'''
from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path( __file__ ).resolve( ).parents[ 1 ]
APP_SOURCE = (ROOT / 'app.py').read_text( encoding='utf-8' )
MAPS_SOURCE = (ROOT / 'maps.py').read_text( encoding='utf-8' )
EXCEL_SOURCE = (ROOT / 'excel.py').read_text( encoding='utf-8' )


class RuntimeBlockerTests( unittest.TestCase ):
    """Guard the two repaired execution contracts against regression."""

    def test_file_enrichment_uses_maps_credential( self ) -> None:
        self.assertIn(
            'excel = Excel( api=cfg.GOOGLEMAPS_API_KEY, cache=cache )',
            APP_SOURCE
        )
        self.assertNotIn(
            'excel = Excel( api=cfg.GOOGLE_API_KEY, cache=cache )',
            APP_SOURCE
        )

    def test_maps_constructor_accepts_explicit_api_key( self ) -> None:
        tree = ast.parse( MAPS_SOURCE )
        cls = next( node for node in tree.body
            if isinstance( node, ast.ClassDef ) and node.name == 'Maps' )
        constructor = next( node for node in cls.body
            if isinstance( node, ast.FunctionDef ) and node.name == '__init__' )
        parameters = [ parameter.arg for parameter in constructor.args.args ]
        self.assertIn( 'api_key', parameters )
        self.assertIn( 'self.maps = Maps( api_key=self.api_key )', EXCEL_SOURCE )

    def test_aggregate_result_guarded_by_numeric_columns( self ) -> None:
        tree = ast.parse( APP_SOURCE )
        aggregates = [ node for node in ast.walk( tree )
            if isinstance( node, ast.If )
            and isinstance( node.test, ast.UnaryOp )
            and isinstance( node.test.op, ast.Not )
            and isinstance( node.test.operand, ast.Name )
            and node.test.operand.id == 'numeric_cols'
            and any( isinstance( child, ast.With ) for child in node.orelse ) ]
        self.assertTrue( aggregates, 'Aggregate controls require a numeric-column guard.' )


if __name__ == '__main__':
    unittest.main( )
