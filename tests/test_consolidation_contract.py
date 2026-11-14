"""Source-level regression tests for the module-consolidation contracts."""
from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, Optional
from urllib.parse import parse_qs, urlparse
import unittest


ROOT = Path( __file__ ).resolve( ).parents[ 1 ]


class ConsolidationContractTests( unittest.TestCase ):
    """Verify consolidated public symbols and Static Maps URL generation."""

    @classmethod
    def setUpClass( cls ) -> None:
        cls.app = (ROOT / 'app.py').read_text( encoding='utf-8' )
        cls.mapping = (ROOT / 'mapping.py').read_text( encoding='utf-8' )
        cls.storage = (ROOT / 'storage.py').read_text( encoding='utf-8' )
        cls.embedders = (ROOT / 'embedders.py').read_text( encoding='utf-8' )

    def test_consolidated_mapping_classes( self ) -> None:
        names = { node.name for node in ast.parse( self.mapping ).body
            if isinstance( node, ast.ClassDef ) }
        self.assertTrue( { 'Map', 'Geocoder', 'DistanceMatrix', 'Place',
            'Timezone', 'StaticMap' } <= names )

    def test_consolidated_storage_classes( self ) -> None:
        names = { node.name for node in ast.parse( self.storage ).body
            if isinstance( node, ast.ClassDef ) }
        self.assertTrue( { 'BaseCache', 'InMemoryCache', 'SQLiteCache',
            'SQLiteDatabase', 'ChromaStore', 'PineconeStore' } <= names )

    def test_processing_and_identifier_contracts( self ) -> None:
        app_names = { node.name for node in ast.parse( self.app ).body
            if isinstance( node, ast.FunctionDef ) }
        embedding_names = { node.name for node in ast.parse( self.embedders ).body
            if isinstance( node, ast.FunctionDef ) }
        self.assertTrue( { 'chunk_documents', 'create_embeddings',
            'store_documents', 'render_loading_tabs', 'render_mode_document_tabs',
            'render_web_document_processing' } <= app_names )
        self.assertTrue( { 'chunk_identifier', 'vector_document_ids' } <=
            embedding_names )

    def test_public_package_exports_follow_consolidation( self ) -> None:
        source = (ROOT / '__init__.py').read_text( encoding='utf-8' )
        tree = ast.parse( source )
        exports = next( node.value for node in tree.body if isinstance( node, ast.Assign )
            and any( isinstance( target, ast.Name ) and target.id == 'EXPORTS'
                for target in node.targets ) )
        mapping = ast.literal_eval( exports )
        for name in ( 'Map', 'Maps', 'Geocoder', 'Place', 'DistanceMatrix',
            'Timezone', 'StaticMap' ):
            self.assertEqual( 'mapping', mapping[ name ] )
        for name in ( 'BaseCache', 'InMemoryCache', 'SQLiteCache',
            'SQLiteDatabase', 'ChromaStore', 'PineconeStore' ):
            self.assertEqual( 'storage', mapping[ name ] )

    def test_removed_modules_have_no_stale_application_imports( self ) -> None:
        removed = { 'maps', 'places', 'geocode', 'distances', 'timezones',
            'staticmaps', 'pipelines', 'chunk_ids', 'caches' }
        tree = ast.parse( self.app )
        for node in ast.walk( tree ):
            if isinstance( node, ast.ImportFrom ) and node.module:
                self.assertNotIn( node.module, removed )
        self.assertFalse( (ROOT / 'stores' / 'vector.py').exists( ) )

    def test_static_map_pin_builds_valid_google_url( self ) -> None:
        import urllib.parse

        module = ast.parse( self.mapping )
        klass = next( node for node in module.body if isinstance( node, ast.ClassDef )
            and node.name == 'StaticMap' )
        guard = next( node for node in module.body if isinstance( node, ast.FunctionDef )
            and node.name == 'throw_if' )
        environment = { 'Optional': Optional, 'Dict': Dict,
            'urlencode': urllib.parse.urlencode,
            'cfg': SimpleNamespace( GOOGLEMAPS_API_KEY='test-key' ) }
        isolated = ast.Module( body=[ guard, klass ], type_ignores=[ ] )
        exec( compile( ast.fix_missing_locations( isolated ), '<mapping>', 'exec' ),
            environment )
        url = environment[ 'StaticMap' ]( ).pin( 38.8977, -77.0365 )
        parsed = urlparse( url )
        params = parse_qs( parsed.query )
        self.assertEqual( 'maps.googleapis.com', parsed.hostname )
        self.assertEqual( '/maps/api/staticmap', parsed.path )
        self.assertEqual( [ '38.8977,-77.0365' ], params[ 'center' ] )
        self.assertEqual( [ 'test-key' ], params[ 'key' ] )


if __name__ == '__main__':
    unittest.main( )
