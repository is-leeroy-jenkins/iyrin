"""Regression test for Site Crawler scraped-text presentation."""
from __future__ import annotations

import ast
from pathlib import Path
import unittest


SOURCE = (Path( __file__ ).resolve( ).parents[ 1 ] / 'pipelines.py').read_text(
    encoding='utf-8' )


class SiteCrawlerDisplayTests( unittest.TestCase ):
    """Ensure the Scraped tab displays document text rather than a data grid."""

    def test_scraped_tab_displays_page_content( self ) -> None:
        tree = ast.parse( SOURCE )
        renderer = next( node for node in tree.body
            if isinstance( node, ast.FunctionDef )
            and node.name == 'render_web_document_processing' )
        tab = next( node for node in ast.walk( renderer )
            if isinstance( node, ast.With )
            and isinstance( node.items[ 0 ].context_expr, ast.Name )
            and node.items[ 0 ].context_expr.id == 'loaded_tab' )
        section = ast.get_source_segment( SOURCE, tab )
        self.assertIn( "document.page_content for document in documents", section )
        self.assertIn( "st.text_area( 'Scraped Text'", section )
        self.assertNotIn( 'st.data_editor(', section )

    def test_other_tabs_remain_present( self ) -> None:
        self.assertIn( "with chunks_tab:", SOURCE )
        self.assertIn( "with embeddings_tab:", SOURCE )


if __name__ == '__main__':
    unittest.main( )
