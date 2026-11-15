"""Regression tests for schema-aware Interactive Map metrics and database reads.

Purpose:
    Confirm all active filters drive map counts, coordinate validity is evaluated
    after filtering, table profiles use the current schema, and SQL identifiers
    are validated against actual SQLite metadata.
"""
from __future__ import annotations

import ast
from pathlib import Path
import sqlite3
from types import SimpleNamespace
from typing import Dict, List
import unittest

import pandas as pd


ROOT = Path( __file__ ).resolve( ).parents[ 1 ]


def load_app_functions( ) -> dict:
    """Compile selected real application functions without executing Streamlit.

    Purpose:
        Exercise the actual map-filter and coordinate-validation functions.

    Returns:
        dict: Namespace containing the target application functions.
    """
    source = (ROOT / 'app.py').read_text( encoding='utf-8' )
    tree = ast.parse( source )
    names = { 'filter_map_records', 'get_map_coordinate_mask',
        'get_reports_map_fields' }
    methods = [ node for node in tree.body if isinstance( node, ast.FunctionDef )
        and node.name in names ]
    if { node.name for node in methods } != names:
        raise AssertionError( 'Map implementation functions are missing.' )
    namespace = { 'pd': pd, 'Dict': Dict, 'List': List,
        'throw_if': lambda name, value: (
            (_ for _ in [ ]).throw( ValueError( name ) ) if value is None else None ),
        'create_schema': lambda table: [ (0, name) for name in
            [ 'ID', 'Year', 'CountryName', 'State', 'Shape', 'Latitude', 'Longitude',
                'Summary', 'Name', 'RefreshId', 'ObservedAt', 'EntityType',
                'EntityId', 'Source', 'City', 'Month', 'Day', 'Type', 'Agency' ] ] }
    module = ast.fix_missing_locations( ast.Module( body=methods, type_ignores=[ ] ) )
    exec( compile( module, str( ROOT / 'app.py' ), 'exec' ), namespace )
    return namespace


class InteractiveMapMetricTests( unittest.TestCase ):
    """Validate shared filter, count, and map-coordinate semantics.

    Attributes:
        functions (dict): Isolated application function implementations.
        df_source (pd.DataFrame): Geographic records containing valid and invalid locations.
    """

    def setUp( self ) -> None:
        """Prepare a cross-filtering fixture with invalid coordinates.

        Returns:
            None: Sets up each test's dataset and isolated functions.
        """
        self.functions = load_app_functions( )
        self.df_source = pd.DataFrame( [
            { 'State': 'AR', 'Shape': 'CHANGING', 'Latitude': 35.1,
                'Longitude': -92.1 },
            { 'State': 'AR', 'Shape': 'CHANGING', 'Latitude': None,
                'Longitude': -92.2 },
            { 'State': 'AR', 'Shape': 'LIGHT', 'Latitude': 0.0,
                'Longitude': 0.0 },
            { 'State': 'VA', 'Shape': 'CHANGING', 'Latitude': 38.2,
                'Longitude': -77.2 },
            { 'State': 'VA', 'Shape': 'LIGHT', 'Latitude': 100.0,
                'Longitude': -77.3 },
        ] )

    def counts( self, selected_filters: dict ) -> tuple:
        """Return total, mapped and invalid counts for the selected filters.

        Args:
            selected_filters (dict): Filter selections for the fixture.

        Returns:
            tuple: Total, valid and invalid record counts.
        """
        df_filtered = self.functions[ 'filter_map_records' ](
            self.df_source, selected_filters )
        mask = self.functions[ 'get_map_coordinate_mask' ]( df_filtered )
        total = len( df_filtered )
        mapped = int( mask.sum( ) )
        return total, mapped, total - mapped

    def test_unfiltered_metrics_classify_every_record( self ) -> None:
        """Include invalid geographic records in unfiltered totals."""
        self.assertEqual( (5, 2, 3), self.counts( { } ) )

    def test_compound_filters_update_all_counts( self ) -> None:
        """Apply AND between State and Shape without dropping invalid records."""
        self.assertEqual( (2, 1, 1),
            self.counts( { 'State': [ 'AR' ], 'Shape': [ 'CHANGING' ] } ) )

    def test_multiple_values_in_one_field_use_or( self ) -> None:
        """Preserve OR semantics for selected values within one filter."""
        self.assertEqual( (3, 2, 1), self.counts(
            { 'State': [ 'AR', 'VA' ], 'Shape': [ 'CHANGING' ] } ) )

    def test_no_matching_rows_produce_zero_counts( self ) -> None:
        """Report zero metrics without showing unrelated fallback records."""
        self.assertEqual( (0, 0, 0), self.counts(
            { 'State': [ 'DC' ], 'Shape': [ 'CHANGING' ] } ) )

    def test_only_invalid_coordinates_still_count( self ) -> None:
        """Count matching records without attempting to map invalid coordinates."""
        self.assertEqual( (1, 0, 1), self.counts(
            { 'State': [ 'AR' ], 'Shape': [ 'LIGHT' ] } ) )

    def test_coordinate_string_and_out_of_range_validation( self ) -> None:
        """Accept geographic strings but reject invalid numeric coordinates."""
        df_values = pd.DataFrame( [
            { 'Latitude': '38.123', 'Longitude': '-77.456' },
            { 'Latitude': 'bad', 'Longitude': '-77.456' },
            { 'Latitude': '0', 'Longitude': '0' },
        ] )
        mask = self.functions[ 'get_map_coordinate_mask' ]( df_values )
        self.assertEqual( [ True, False, False ], mask.tolist( ) )

    def test_current_schema_profiles_select_expected_fields( self ) -> None:
        """Map the current Observations and World tables without legacy aliases."""
        fields = self.functions[ 'get_reports_map_fields' ]( 'Observations' )
        self.assertIn( 'CountryName', fields )
        self.assertIn( 'Shape', fields )
        self.assertNotIn( 'Country', fields )
        world = self.functions[ 'get_reports_map_fields' ]( 'World' )
        self.assertIn( 'RefreshId', world )
        self.assertIn( 'EntityType', world )

    def test_rendering_contract_uses_filtered_metrics( self ) -> None:
        """Keep metric calculation after filters and before the plotting limit."""
        source = (ROOT / 'app.py').read_text( encoding='utf-8' )
        start = source.index( 'def create_reports_map(' )
        end = source.index( 'def compose_location_query(', start )
        body = source[ start:end ]
        self.assertLess( body.index( 'df_filtered = filter_map_records(' ),
            body.index( "metric_c1.metric( 'Total Records'" ) )
        self.assertLess( body.index( "metric_c2.metric( 'Mapped Records'" ),
            body.index( "df_base_map = df_base_map.head( max_records )" ) )
        self.assertIn( 'filter_prefix =', body )
        self.assertIn( "'Observations': {", body )
        self.assertIn( "'Military Installations': {", body )


class SelectedColumnDatabaseTests( unittest.TestCase ):
    """Validate safe selected-column SQL retrieval against an in-memory database.

    Attributes:
        connection (sqlite3.Connection): Test SQLite connection.
        reader (object): Database object using the production read method.
    """

    def setUp( self ) -> None:
        """Construct a SQLite fixture and bind the production reader method.

        Returns:
            None: Initializes the database and method under test.
        """
        self.connection = sqlite3.connect( ':memory:' )
        self.connection.execute(
            'CREATE TABLE "Military Installations" '
            '(ID INTEGER, Name TEXT, Latitude REAL, Longitude REAL, Notes TEXT)' )
        self.connection.execute(
            'INSERT INTO "Military Installations" VALUES (1, ?, 38.8, -77.1, ?)',
            ('Fort Example', 'large unneeded text') )
        tree = ast.parse( (ROOT / 'storage.py').read_text( encoding='utf-8' ) )
        source_class = next( node for node in tree.body
            if isinstance( node, ast.ClassDef ) and node.name == 'SQLiteDatabase' )
        method = next( node for node in source_class.body
            if isinstance( node, ast.FunctionDef ) and node.name == 'read_selected_columns' )
        cls = ast.ClassDef( name='Reader', bases=[ ], keywords=[ ],
            body=[ method ], decorator_list=[ ] )
        module = ast.fix_missing_locations( ast.Module( body=[ cls ], type_ignores=[ ] ) )
        namespace = { 'List': List, 'pd': pd,
            'throw_if': lambda name, value: (
                (_ for _ in [ ]).throw( ValueError( name ) )
                if value is None or value == [ ] else None ),
            'Error': Exception,
            'Logger': lambda: SimpleNamespace( write=lambda error: None ) }
        exec( compile( module, str( ROOT / 'storage.py' ), 'exec' ), namespace )
        self.reader = namespace[ 'Reader' ]( )
        self.reader.create_connection = lambda: self.connection
        self.reader.create_read_connection = lambda: self.connection
        self.reader.list_tables = lambda: [ 'Military Installations' ]
        self.reader.create_schema = lambda table: self.connection.execute(
            'PRAGMA table_info("Military Installations")' ).fetchall( )

    def tearDown( self ) -> None:
        """Close the SQLite fixture after each test."""
        self.connection.close( )

    def test_selected_columns_exclude_unrequested_large_fields( self ) -> None:
        """Read geographic columns and omit unrelated long text."""
        df_rows = self.reader.read_selected_columns( 'Military Installations',
            [ 'Name', 'Latitude', 'Longitude' ] )
        self.assertEqual( [ 'Name', 'Latitude', 'Longitude' ],
            list( df_rows.columns ) )
        self.assertEqual( 1, len( df_rows ) )

    def test_selected_column_reader_bypasses_pandas_sql_adapter( self ) -> None:
        """Read selected columns through SQLite cursors without pandas SQL adapter."""
        original = pd.read_sql_query
        try:
            def fail_sql_adapter( query: str, connection: object ) -> pd.DataFrame:
                """Reject invocation of the previously failing adapter path.

                Args:
                    query (str): SQL text.
                    connection (object): SQLite connection.

                Returns:
                    pd.DataFrame: Never returned.
                """
                raise AssertionError( 'pandas.read_sql_query must not be called' )

            pd.read_sql_query = fail_sql_adapter
            df_records = self.reader.read_selected_columns( 'Military Installations',
                [ 'Name', 'Latitude', 'Longitude' ] )
            self.assertEqual( 1, len( df_records ) )
            self.assertEqual( 'Fort Example', df_records.iloc[ 0 ][ 'Name' ] )
        finally:
            pd.read_sql_query = original

    def test_selected_column_reader_preserves_empty_frame_columns( self ) -> None:
        """Return requested column names even when a table has zero records."""
        self.connection.execute( 'DELETE FROM "Military Installations"' )
        df_records = self.reader.read_selected_columns( 'Military Installations',
            [ 'Name', 'Latitude', 'Longitude' ] )
        self.assertTrue( df_records.empty )
        self.assertEqual( [ 'Name', 'Latitude', 'Longitude' ],
            list( df_records.columns ) )

    def test_unknown_column_and_table_are_rejected( self ) -> None:
        """Reject user-provided SQL identifiers outside the live schema."""
        with self.assertRaises( Exception ):
            self.reader.read_selected_columns( 'Military Installations', [ 'Unknown' ] )
        with self.assertRaises( Exception ):
            self.reader.read_selected_columns( 'Other Table', [ 'Name' ] )


if __name__ == '__main__':
    unittest.main( )
