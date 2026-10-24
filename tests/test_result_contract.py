"""Regression tests for core.Result and the WebCrawler result contract."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from core import Result


ROOT = Path( __file__ ).resolve( ).parents[ 1 ]


class ResultTests( unittest.TestCase ):
    """Exercise both supported Result construction pathways."""

    def test_crawler_keyword_constructor( self ) -> None:
        result = Result( url='https://example.com', status=200, text='Hello',
            html='<p>Hello</p>', headers={ 'Content-Type': 'text/html' } )
        self.assertEqual( 'https://example.com', result.url )
        self.assertEqual( 200, result.status_code )
        self.assertEqual( 'Hello', result.text )
        self.assertEqual( '<p>Hello</p>', result.html )
        self.assertTrue( result.has_html )
        self.assertEqual( result.html, result.to_dict( )[ 'html' ] )
        self.assertIsNone( result.response )

    def test_empty_html_is_not_misclassified( self ) -> None:
        result = Result( url='https://example.com', status=200, text='Plain text' )
        self.assertFalse( result.has_html )
        self.assertEqual( { }, result.headers )
        self.assertFalse( result.to_dict( )[ 'html' ] )

    def test_existing_response_constructor( self ) -> None:
        from requests import Response
        response = Response( )
        response.status_code = 201
        response.url = 'https://example.com/page'
        response._content = b'<h1>Ready</h1>'
        response.encoding = 'utf-8'
        response.headers[ 'Content-Type' ] = 'text/html; charset=utf-8'
        result = Result( response )
        self.assertIs( response, result.response )
        self.assertEqual( 201, result.status_code )
        self.assertEqual( response.text, result.html )
        self.assertTrue( result.has_html )
        self.assertIn( 'html', dir( result ) )

    def test_result_headers_are_copied( self ) -> None:
        headers = { 'X-Test': 'before' }
        result = Result( url='https://example.com', headers=headers )
        headers[ 'X-Test' ] = 'after'
        self.assertEqual( 'before', result.headers[ 'X-Test' ] )

    def test_crawler_paths_construct_supported_result( self ) -> None:
        source = (ROOT / 'fetchers.py').read_text( encoding='utf-8' )
        tree = ast.parse( source )
        crawler = next( node for node in tree.body if isinstance( node, ast.ClassDef )
            and node.name == 'WebCrawler' )
        fetch = next( node for node in crawler.body if isinstance( node, ast.FunctionDef )
            and node.name == 'fetch' )
        constructions = [ node for node in ast.walk( fetch ) if isinstance( node, ast.Call )
            and isinstance( node.func, ast.Name ) and node.func.id == 'Result' ]
        self.assertEqual( 2, len( constructions ) )
        for call in constructions:
            self.assertEqual( { 'url', 'status', 'text', 'html', 'headers' },
                { keyword.arg for keyword in call.keywords } )


if __name__ == '__main__':
    unittest.main( )
