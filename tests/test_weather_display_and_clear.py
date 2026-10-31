"""Verify API Loaded-tab text presentation and Google Weather clear behavior."""
from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path( __file__ ).resolve( ).parents[ 1 ]
APP = (ROOT / 'app.py').read_text( encoding='utf-8' )
PIPELINES = (ROOT / 'pipelines.py').read_text( encoding='utf-8' )


class WeatherDisplayAndClearTests( unittest.TestCase ):
    """Preserve document display and remove stale weather processing results."""

    def test_loaded_tab_uses_document_text( self ) -> None:
        module = ast.parse( PIPELINES )
        renderer = next( node for node in module.body
            if isinstance( node, ast.FunctionDef )
            and node.name == 'render_mode_document_tabs' )
        loaded_tab = next( node for node in ast.walk( renderer )
            if isinstance( node, ast.With )
            and isinstance( node.items[ 0 ].context_expr, ast.Name )
            and node.items[ 0 ].context_expr.id == 'loaded_tab' )
        content = ast.get_source_segment( PIPELINES, loaded_tab )
        self.assertIn( 'document.page_content for document in documents', content )
        self.assertIn( "st.text_area( 'Loaded Document Text'", content )
        self.assertNotIn( 'st.data_editor(', content )

    def test_chunks_and_embeddings_remain_data_editors( self ) -> None:
        module = ast.parse( PIPELINES )
        renderer = next( node for node in module.body
            if isinstance( node, ast.FunctionDef )
            and node.name == 'render_mode_document_tabs' )
        for name in ( 'chunks_tab', 'embeddings_tab' ):
            tab = next( node for node in ast.walk( renderer )
                if isinstance( node, ast.With )
                and isinstance( node.items[ 0 ].context_expr, ast.Name )
                and node.items[ 0 ].context_expr.id == name )
            self.assertIn( 'st.data_editor(', ast.get_source_segment( PIPELINES, tab ) )

    def test_google_weather_clear_resets_derived_documents( self ) -> None:
        start = APP.index( "key='weather_google_clear'" )
        end = APP.index( "render_source_processing_controls( 'weather'", start )
        clear = APP[ start:end ]
        for key in ( 'weather_documents', 'weather_chunks', 'weather_embeddings',
                'weather_document_signature', 'weather_last_result',
                'weather_last_source', 'weather_vector_store' ):
            self.assertIn( key, clear )


if __name__ == '__main__':
    unittest.main( )
