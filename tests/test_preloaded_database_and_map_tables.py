"""Regression tests for the pre-hydrated database and renamed Interactive Map tables.

Purpose:
    Ensure Iyrin never creates a substitute operational database, detects Git LFS
    pointers, and recognizes the current UAP, Military, and Pollution table names.
"""
from __future__ import annotations

import ast
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Dict, List
import unittest


ROOT = Path( __file__ ).resolve( ).parents[ 1 ]
APP = (ROOT / 'app.py').read_text( encoding='utf-8' )
STORAGE = (ROOT / 'storage.py').read_text( encoding='utf-8' )


class PrehydratedDatabaseTests( unittest.TestCase ):
    """Validate safe operational database initialization and connection modes.

    Attributes:
        directory (TemporaryDirectory): Isolated test directory.
        db_path (Path): Configured test database path.
        database (object): Isolated production SQLiteDatabase connection methods.
        cfg (SimpleNamespace): Test database path configuration.
    """

    def setUp( self ) -> None:
        """Create an isolated SQLiteDatabase exposing its real connection methods.

        Returns:
            None: Initializes the fixture and compiled production methods.
        """
        self.directory = TemporaryDirectory( )
        self.db_path = Path( self.directory.name ) / 'stores' / 'sqlite' / 'data.db'
        tree = ast.parse( STORAGE )
        source_class = next( item for item in tree.body
            if isinstance( item, ast.ClassDef ) and item.name == 'SQLiteDatabase' )
        methods = [ method for method in source_class.body
            if isinstance( method, ast.FunctionDef ) and method.name in {
                'validate_database_file', 'create_connection', 'create_read_connection' } ]
        self.assertEqual( 3, len( methods ) )
        cls = ast.ClassDef( name='TestDatabase', bases=[ ], keywords=[ ],
            body=methods, decorator_list=[ ] )
        module = ast.fix_missing_locations( ast.Module( body=[ cls ], type_ignores=[ ] ) )
        self.cfg = SimpleNamespace( DB_PATH=str( self.db_path ) )
        namespace = { 'Path': Path, 'sqlite3': sqlite3, 'cfg': self.cfg }
        exec( compile( module, str( ROOT / 'storage.py' ), 'exec' ), namespace )
        self.database = namespace[ 'TestDatabase' ]( )

    def tearDown( self ) -> None:
        """Remove the temporary SQLite test database."""
        self.directory.cleanup( )

    def test_missing_database_does_not_get_created( self ) -> None:
        """Reject a missing operational database instead of creating an empty file."""
        self.db_path.parent.mkdir( parents=True, exist_ok=True )
        with self.assertRaises( FileNotFoundError ):
            self.database.create_connection( )
        self.assertFalse( self.db_path.exists( ) )

    def test_git_lfs_pointer_is_rejected( self ) -> None:
        """Reject text placeholders produced by an unhydrated Git LFS checkout."""
        self.db_path.parent.mkdir( parents=True, exist_ok=True )
        self.db_path.write_text( 'version https://git-lfs.github.com/spec/v1\n'
            'oid sha256:abcdef\nsize 22446080\n', encoding='utf-8' )
        with self.assertRaises( ValueError ):
            self.database.create_read_connection( )
        self.assertTrue( self.db_path.is_file( ) )

    def test_preexisting_database_supports_reads_and_explicit_writes( self ) -> None:
        """Keep the hydrated file and allow authorized write connections."""
        self.db_path.parent.mkdir( parents=True, exist_ok=True )
        with sqlite3.connect( self.db_path ) as connection:
            connection.execute( 'CREATE TABLE UAP (ID INTEGER PRIMARY KEY, Latitude REAL, '
                'Longitude REAL)' )
            connection.execute( 'INSERT INTO UAP VALUES (1, 38.9, -77.0)' )
        with self.database.create_read_connection( ) as connection:
            result = connection.execute( 'SELECT COUNT(*) FROM UAP' ).fetchone( )
            self.assertEqual( 1, result[ 0 ] )
            with self.assertRaises( sqlite3.OperationalError ):
                connection.execute( 'INSERT INTO UAP VALUES (2, 38.8, -77.1)' )
        with self.database.create_connection( ) as connection:
            connection.execute( 'INSERT INTO UAP VALUES (2, 38.8, -77.1)' )
        with self.database.create_read_connection( ) as connection:
            self.assertEqual( 2, connection.execute(
                'SELECT COUNT(*) FROM UAP' ).fetchone( )[ 0 ] )


class RenamedMapTableTests( unittest.TestCase ):
    """Check the active map profiles and default dataset use the live table names.

    Attributes:
        source (str): Current application source code.
    """

    def test_default_table_is_uap_and_database_path_is_rooted( self ) -> None:
        """Use UAP as the default and resolve database relative to config.py."""
        config = (ROOT / 'config.py').read_text( encoding='utf-8' )
        self.assertIn( "DEFAULT_DATA = r'UAP'", config )
        self.assertIn( "DB_PATH = str( BASE_DIR / 'stores' / 'sqlite' / 'data.db' )", config )

    def test_map_has_explicit_profiles_for_renamed_tables( self ) -> None:
        """Configure the three renamed tables for filters and map tooltips."""
        tree = ast.parse( APP )
        function = next( node for node in tree.body
            if isinstance( node, ast.FunctionDef ) and node.name == 'create_reports_map' )
        body = ast.get_source_segment( APP, function ) or ''
        for table in ( 'UAP', 'Military', 'Pollution' ):
            self.assertIn( f"'{table}': {{", body )

    def test_map_column_selection_respects_actual_schema( self ) -> None:
        """Never request columns that are absent in the operational table."""
        tree = ast.parse( APP )
        method = next( node for node in tree.body
            if isinstance( node, ast.FunctionDef ) and node.name == 'get_reports_map_fields' )
        module = ast.fix_missing_locations( ast.Module( body=[ method ], type_ignores=[ ] ) )
        existing = [ 'ID', 'Year', 'State', 'Shape', 'Latitude', 'Longitude' ]
        namespace = { 'List': List, 'Dict': Dict,
            'throw_if': lambda name, value: None,
            'create_schema': lambda table: [ (0, field) for field in existing ] }
        exec( compile( module, str( ROOT / 'app.py' ), 'exec' ), namespace )
        fields = namespace[ 'get_reports_map_fields' ]( 'UAP' )
        self.assertEqual( existing, fields )

    def test_sidebar_and_excel_import_use_validated_connections( self ) -> None:
        """Prevent sidebar reads and explicit Excel imports from creating empty files."""
        self.assertIn( 'with create_read_connection( ) as connection:', APP )
        self.assertIn( 'conn = create_connection( )', APP )
        self.assertNotIn( 'with sqlite3.connect( cfg.DB_PATH ) as connection:', APP )


if __name__ == '__main__':
    unittest.main( )
