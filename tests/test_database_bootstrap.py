"""Regression tests for first-run database and source-selection contracts."""
import ast
import os
from pathlib import Path
import sqlite3
from types import SimpleNamespace
import unittest
from tempfile import TemporaryDirectory


APP_PATH = Path( __file__ ).resolve( ).parents[ 1 ] / 'app.py'


class BootstrapTests( unittest.TestCase ):
    """Verify the database initializer without importing Streamlit or API SDKs."""

    def setUp( self ) -> None:
        self.source = APP_PATH.read_text( encoding='utf-8' )
        self.module = ast.parse( self.source )

    def test_sqlite_cache_creates_persistent_schema( self ) -> None:
        """Verify the consolidated SQLite cache initializes a new on-disk database."""
        from typing import Any, Dict, Optional

        path = Path( __file__ ).resolve( ).parents[ 1 ] / 'storage.py'
        source = path.read_text( encoding='utf-8' )
        tree = ast.parse( source )
        cache_class = next( node for node in tree.body
            if isinstance( node, ast.ClassDef ) and node.name == 'SQLiteCache' )
        isolated = ast.Module( body=[ cache_class ], type_ignores=[ ] )
        namespace = { 'BaseCache': object, 'sqlite3': sqlite3, 'os': os,
            'Any': Any, 'Dict': Dict, 'Optional': Optional }
        exec( compile( ast.fix_missing_locations( isolated ), str( path ), 'exec' ),
            namespace )
        with TemporaryDirectory( ) as directory:
            database = Path( directory ) / 'cache' / 'data.db'
            cache = namespace[ 'SQLiteCache' ]( str( database ) )
            try:
                self.assertTrue( database.is_file( ) )
                with sqlite3.connect( database ) as connection:
                    tables = { row[ 0 ] for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'" ) }
                    columns = { row[ 1 ] for row in connection.execute(
                        'PRAGMA table_info(kv)' ) }
                self.assertIn( 'kv', tables )
                self.assertTrue( { 'k', 'v', 'expires_at', 'hit_count' } <= columns )
            finally:
                cache.close( )

    def test_external_selector_has_a_matching_branch( self ) -> None:
        self.assertIn( "'Default', 'Database', 'External'", self.source )
        self.assertIn( "elif source == 'External':", self.source )
        self.assertNotIn( "elif source == 'Custom':", self.source )

    def test_default_query_is_guarded_by_table_existence( self ) -> None:
        self.assertIn( "selected_table = cfg.DEFAULT_DATA if source == 'Default' else None",
            self.source )
        self.assertIn( "elif selected_table not in table_options:", self.source )
        self.assertIn( "selected_table = None", self.source )
        self.assertIn( "if selected_table:", self.source )


if __name__ == '__main__':
    unittest.main( )
