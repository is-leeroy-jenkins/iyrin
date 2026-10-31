"""Regression checks for P0 Streamlit rerun performance safeguards."""
from __future__ import annotations

import ast
from pathlib import Path
import unittest


SOURCE = (Path( __file__ ).resolve( ).parents[ 1 ] / 'app.py').read_text(
    encoding='utf-8' )
TREE = ast.parse( SOURCE )


class PerformanceP0Tests( unittest.TestCase ):
    """Ensure expensive operations are gated by active UI and dataset identity."""

    def test_data_management_tabs_are_lazy( self ) -> None:
        guards = [ node for node in ast.walk( TREE )
            if isinstance( node, ast.If )
            and isinstance( node.test, ast.Attribute )
            and node.test.attr == 'open'
            and isinstance( node.test.value, ast.Subscript )
            and isinstance( node.test.value.value, ast.Name )
            and node.test.value.value.id == 'tabs' ]
        self.assertEqual( 10, len( guards ) )
        for guard in guards:
            self.assertTrue( any( isinstance( statement, ast.With )
                for statement in guard.body ) )

    def test_tabs_track_selection( self ) -> None:
        self.assertIn( "on_change='rerun', key='data_management_active_tab'",
            SOURCE )

    def test_sidebar_dataset_load_uses_signature_guard( self ) -> None:
        self.assertIn( "st.session_state.get( '_sidebar_dataset_signature' ) != dataset_signature",
            SOURCE )
        self.assertIn( "st.session_state[ '_sidebar_dataset_signature' ] = dataset_signature",
            SOURCE )
        self.assertIn( 'db_path.stat( ).st_mtime_ns', SOURCE )

    def test_external_upload_changes_invalidate_signature( self ) -> None:
        self.assertIn( 'hashlib.sha256( uploaded.getvalue( ) ).hexdigest( )',
            SOURCE )


if __name__ == '__main__':
    unittest.main( )
