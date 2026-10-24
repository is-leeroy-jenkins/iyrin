"""Installation manifest regression tests for supported loader integrations."""
from pathlib import Path
import tomllib
import unittest


ROOT = Path( __file__ ).resolve( ).parents[ 1 ]


class RuntimeDependencyTests( unittest.TestCase ):
    """Check dependency declarations without installing heavyweight providers."""

    @classmethod
    def setUpClass( cls ) -> None:
        cls.runtime_lines = (ROOT / 'requirements-runtime.txt').read_text(
            encoding='utf-8' ).splitlines( )
        cls.development_lines = (ROOT / 'requirements.txt').read_text(
            encoding='utf-8' ).splitlines( )
        with (ROOT / 'pyproject.toml').open( 'rb' ) as stream:
            cls.metadata = tomllib.load( stream )

    def test_loader_dependencies_are_explicit( self ) -> None:
        runtime = set( self.runtime_lines )
        for package in ( 'boto3', 'langchain-google-community[gcs,speech]',
                'unstructured[pptx]' ):
            with self.subTest( package=package ):
                self.assertIn( package, runtime )

    def test_development_manifest_includes_runtime_dependencies( self ) -> None:
        self.assertFalse( set( self.runtime_lines ) - set( self.development_lines ) -
            { 'pywebview>=5.0; sys_platform == "win32"' } )

    def test_distribution_uses_runtime_manifest( self ) -> None:
        self.assertEqual( [ 'requirements-runtime.txt' ], self.metadata[
            'tool' ][ 'setuptools' ][ 'dynamic' ][ 'dependencies' ][ 'file' ] )

    def test_crawl4ai_is_explicitly_optional( self ) -> None:
        self.assertEqual( [ 'crawl4ai' ], self.metadata[ 'project' ][
            'optional-dependencies' ][ 'crawl' ] )
        self.assertNotIn( 'crawl4ai', self.runtime_lines )

    def test_desktop_reuses_runtime_manifest( self ) -> None:
        desktop = (ROOT / 'requirements-desktop.txt').read_text( encoding='utf-8' )
        self.assertIn( '-r requirements-runtime.txt', desktop )


if __name__ == '__main__':
    unittest.main( )
