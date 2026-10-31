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

    def test_initialize_database_creates_expected_tables( self ) -> None:
        function = next( node for node in self.module.body
            if isinstance( node, ast.FunctionDef ) and node.name == 'initialize_database' )
        namespace = {
            'Path': Path,
            'sqlite3': sqlite3,
            'cfg': SimpleNamespace( DB_PATH='stores/sqlite/data.db' ),
        }
        isolated = ast.Module( body=[ function ], type_ignores=[ ] )
        exec( compile( ast.fix_missing_locations( isolated ), str( APP_PATH ), 'exec' ),
            namespace )
        with TemporaryDirectory( ) as directory:
            original = Path.cwd( )
            try:
                os.chdir( directory )
                namespace[ 'initialize_database' ]( )
                database = Path( 'stores/sqlite/data.db' )
                self.assertTrue( database.is_file( ) )
                with sqlite3.connect( database ) as connection:
                    tables = { row[ 0 ] for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'" ) }
                self.assertTrue( { 'chat_history', 'embeddings', 'Prompts' } <= tables )
                namespace[ 'initialize_database' ]( )
            finally:
                os.chdir( original )

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
