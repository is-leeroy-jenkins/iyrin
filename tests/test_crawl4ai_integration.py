"""Offline regression tests for Crawl4AI and HTTP fallback behavior."""
import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace
import unittest


SOURCE = (Path( __file__ ).resolve( ).parents[ 1 ] / 'fetchers.py').read_text(
    encoding='utf-8' )


class FakeResult:
    def __init__( self, url: str='', status: int=0, text: str='', html: str='',
            headers=None ) -> None:
        self.url = url
        self.status_code = status
        self.text = text
        self.html = html
        self.headers = headers


class CrawlerTests( unittest.TestCase ):
    def build_crawler( self, crawl4ai, response ) -> object:
        module = ast.parse( SOURCE )
        cls = next( node for node in module.body
            if isinstance( node, ast.ClassDef ) and node.name == 'WebCrawler' )
        method = next( node for node in cls.body
            if isinstance( node, ast.FunctionDef ) and node.name == 'fetch' )
        isolated = ast.Module( body=[ method ], type_ignores=[ ] )
        environment = {
            'asyncio': asyncio,
            'crawl4ai': crawl4ai,
            'requests': SimpleNamespace( get=lambda url, headers, timeout: response ),
            'Result': FakeResult,
            'throw_if': lambda name, value: None,
            'Error': RuntimeError,
        }
        exec( compile( ast.fix_missing_locations( isolated ), '<crawler>', 'exec' ),
            environment )
        instance = SimpleNamespace(
            raw_url=None, raw_html=None, result=None, headers={ },
            timeout=0, html_to_text=lambda html: html.replace( '<p>', '' ).replace(
                '</p>', '' ) )
        return SimpleNamespace(
            fetch=lambda url, time=10: environment[ 'fetch' ]( instance, url, time ),
            crawler=instance )

    def test_async_crawl_success( self ) -> None:
        payload = SimpleNamespace( success=True, url='https://example.org/redirect',
            html='<p>Rendered</p>', status_code=202, response_headers={ 'X': 'yes' } )

        class AsyncCrawler:
            async def __aenter__( self ):
                return self

            async def __aexit__( self, exc_type, exc, tb ):
                return False

            async def arun( self, url, config ):
                return payload

        crawler_api = SimpleNamespace(
            AsyncWebCrawler=AsyncCrawler,
            CrawlerRunConfig=lambda page_timeout: SimpleNamespace(
                page_timeout=page_timeout ) )
        fake_response = SimpleNamespace( url='', text='', status_code=200, headers={ },
            raise_for_status=lambda: None )
        runner = self.build_crawler( crawler_api, fake_response )
        result = runner.fetch( 'https://example.org', 8 )
        self.assertEqual( 'Rendered', result.text )
        self.assertEqual( 202, result.status_code )
        self.assertEqual( 'https://example.org/redirect', result.url )

    def test_failed_crawl_uses_requests_fallback( self ) -> None:
        class AsyncCrawler:
            async def __aenter__( self ):
                return self

            async def __aexit__( self, exc_type, exc, tb ):
                return False

            async def arun( self, url, config ):
                return SimpleNamespace( success=False, html='', url=url )

        api = SimpleNamespace( AsyncWebCrawler=AsyncCrawler,
            CrawlerRunConfig=lambda page_timeout: page_timeout )
        response = SimpleNamespace( url='https://example.org/final',
            text='<p>Fallback</p>', status_code=200, headers={ 'X': 'fallback' },
            raise_for_status=lambda: None )
        runner = self.build_crawler( api, response )
        result = runner.fetch( 'https://example.org' )
        self.assertEqual( 'Fallback', result.text )
        self.assertEqual( 'https://example.org/final', result.url )

    def test_absent_crawl4ai_uses_http( self ) -> None:
        response = SimpleNamespace( url='https://example.org', text='<p>HTTP</p>',
            status_code=200, headers={ }, raise_for_status=lambda: None )
        runner = self.build_crawler( None, response )
        self.assertEqual( 'HTTP', runner.fetch( 'https://example.org' ).text )


if __name__ == '__main__':
    unittest.main( )
