"""Regression checks for the shared Loading-mode LangChain document display."""
from __future__ import annotations

import ast
from pathlib import Path
import unittest


SOURCE = (Path( __file__ ).resolve( ).parents[ 1 ] / 'pipelines.py').read_text(
    encoding='utf-8' )


class LoadingDocumentDisplayTests( unittest.TestCase ):
    """All Loading-mode sources show document text with tabular derived results."""

    def test_loaded_text_and_derived_editors( self ) -> None:
        module = ast.parse( SOURCE )
        renderer = next( node for node in module.body
            if isinstance( node, ast.FunctionDef )
            and node.name == 'render_loading_tabs' )

        tabs = { node.items[ 0 ].context_expr.id: node
            for node in ast.walk( renderer )
            if isinstance( node, ast.With )
            and isinstance( node.items[ 0 ].context_expr, ast.Name )
            and node.items[ 0 ].context_expr.id in
                ( 'loaded_tab', 'chunks_tab', 'embeddings_tab' ) }

        loaded = ast.get_source_segment( SOURCE, tabs[ 'loaded_tab' ] )
        self.assertIn( 'document.page_content for document in documents', loaded )
        self.assertIn( "st.text_area( 'Loaded Document Text'", loaded )
        self.assertNotIn( 'st.data_editor(', loaded )

        for name in ( 'chunks_tab', 'embeddings_tab' ):
            source = ast.get_source_segment( SOURCE, tabs[ name ] )
            self.assertIn( 'st.data_editor(', source )


if __name__ == '__main__':
    unittest.main( )
