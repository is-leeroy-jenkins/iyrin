"""Regression tests for WebCrawler HTML extraction."""
import ast
from pathlib import Path
import unittest

from bs4 import BeautifulSoup

SOURCE = (Path( __file__ ).resolve( ).parents[ 1 ] / 'loaders.py').read_text(
    encoding='utf-8' )


class WebCrawlerExtractionTests( unittest.TestCase ):
    def test_extractor_removes_html_infrastructure( self ) -> None:
        module = ast.parse( SOURCE )
        helper = next( node for node in module.body
            if isinstance( node, ast.FunctionDef ) and node.name == 'extract_web_text' )
        environment = {
            'BeautifulSoup': BeautifulSoup,
            'throw_if': lambda name, value: None,
        }
        exec( compile( ast.fix_missing_locations(
            ast.Module( body=[ helper ], type_ignores=[ ] ) ), '<extractor>', 'exec' ),
            environment )
        html = ( '<html><head><meta name="test"><link rel="stylesheet"></head>'
            '<body><nav>Navigation noise</nav><main><h1>EPA heading</h1>'
            '<p>Protect human health.</p><script>ignore_me()</script></main>'
            '<footer>Footer noise</footer></body></html>' )
        extracted = environment[ 'extract_web_text' ]( html )
        self.assertIn( 'EPA heading', extracted )
        self.assertIn( 'Protect human health.', extracted )
        self.assertNotIn( '<', extracted )
        self.assertNotIn( 'Navigation noise', extracted )
        self.assertNotIn( 'ignore_me', extracted )
        self.assertNotIn( 'Footer noise', extracted )

    def test_both_recursive_constructors_use_extractor( self ) -> None:
        module = ast.parse( SOURCE )
        crawler = next( node for node in module.body
            if isinstance( node, ast.ClassDef ) and node.name == 'WebCrawler' )
        for name in ('__init__', 'load_recursive'):
            method = next( node for node in crawler.body
                if isinstance( node, ast.FunctionDef ) and node.name == name )
            calls = [ node for node in ast.walk( method )
                if isinstance( node, ast.Call )
                and isinstance( node.func, ast.Name )
                and node.func.id == 'RecursiveUrlLoader' ]
            self.assertEqual( 1, len( calls ) )
            extractor = next( (keyword.value for keyword in calls[ 0 ].keywords
                if keyword.arg == 'extractor'), None )
            self.assertIsInstance( extractor, ast.Name )
            self.assertEqual( 'extract_web_text', extractor.id )


if __name__ == '__main__':
    unittest.main( )
