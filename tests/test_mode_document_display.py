"""Regression checks for API-mode LangChain document previews."""
from __future__ import annotations

import ast
from pathlib import Path
import unittest


SOURCE = (Path( __file__ ).resolve( ).parents[ 1 ] / 'pipelines.py').read_text(
    encoding='utf-8' )


class ModeDocumentDisplayTests( unittest.TestCase ):
    """Ensure only the Loaded tab switches from a grid to extracted text."""

    def test_loaded_displays_document_text( self ) -> None:
        module = ast.parse( SOURCE )
        renderer = next( node for node in module.body
            if isinstance( node, ast.FunctionDef )
            and node.name == 'render_mode_document_tabs' )
        tabs = { item.items[ 0 ].context_expr.id: item
            for item in ast.walk( renderer )
            if isinstance( item, ast.With )
            and isinstance( item.items[ 0 ].context_expr, ast.Name )
            and item.items[ 0 ].context_expr.id in
                ( 'loaded_tab', 'chunks_tab', 'embeddings_tab' ) }

        loaded_source = ast.get_source_segment( SOURCE, tabs[ 'loaded_tab' ] )
        self.assertIn( "document.page_content for document in documents", loaded_source )
        self.assertIn( "st.text_area( 'Loaded Text'", loaded_source )
        self.assertNotIn( 'st.data_editor(', loaded_source )

        for name in ( 'chunks_tab', 'embeddings_tab' ):
            tab_source = ast.get_source_segment( SOURCE, tabs[ name ] )
            self.assertIn( 'st.data_editor(', tab_source )


if __name__ == '__main__':
    unittest.main( )
