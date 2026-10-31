"""Executable tests for file-upload loaders, metadata and lifecycle."""
import csv
import io
import json
from pathlib import Path
import unittest
from xml.etree import ElementTree

from upload_documents import load_uploaded_document


class UploadedFile:
    def __init__( self, name: str, contents: bytes ) -> None:
        self.name = name
        self.contents = contents

    def getvalue( self ) -> bytes:
        return self.contents


class Document:
    def __init__( self, text: str ) -> None:
        self.page_content = text
        self.metadata = { }


class FileUploadRuntimeTests( unittest.TestCase ):
    def test_content_and_metadata_per_format( self ) -> None:
        payloads = {
            'sample.txt': b'Plain document text',
            'sample.csv': b'name,value\nalpha,7\n',
            'sample.json': b'{"name":"alpha","value":7}',
            'sample.xml': b'<record><name>alpha</name></record>',
            'sample.html': b'<p>alpha</p>',
        }
        for filename, contents in payloads.items( ):
            with self.subTest( filename=filename ):
                observed = { }

                class Loader:
                    def load( self, filepath: str ) -> list:
                        path = Path( filepath )
                        observed[ 'temporary_path' ] = path
                        self_test.assertTrue( path.exists( ) )
                        data = path.read_text( encoding='utf-8' )
                        if filename.endswith( '.csv' ):
                            content = next( csv.DictReader( io.StringIO( data ) ) )[ 'name' ]
                        elif filename.endswith( '.xml' ):
                            content = ElementTree.fromstring( data ).findtext( 'name' )
                        elif filename.endswith( '.json' ):
                            raise AssertionError( 'JSON should include is_text=False' )
                        else:
                            content = data
                        return [ Document( content ) ]

                class HtmlLoader:
                    def load( self, path: str ) -> list:
                        observed[ 'temporary_path' ] = Path( path )
                        return [ Document( Path( path ).read_text( encoding='utf-8' ) ) ]

                class JsonLoader:
                    def load( self, filepath: str, is_text: bool=True ) -> list:
                        self_test.assertFalse( is_text )
                        observed[ 'temporary_path' ] = Path( filepath )
                        return [ Document( str( json.loads(
                            Path( filepath ).read_text( encoding='utf-8' ) )[ 'name' ] ) ) ]

                def promote( documents: list, loader_name: str ) -> int:
                    observed[ 'documents' ] = documents
                    observed[ 'loader_name' ] = loader_name
                    return len( documents )

                self_test = self
                loaders = { suffix: (JsonLoader if suffix == '.json' else
                    HtmlLoader if suffix == '.html' else Loader)
                    for suffix in ( '.txt', '.csv', '.json', '.xml', '.html' ) }
                count = load_uploaded_document(
                    UploadedFile( filename, contents ), loaders, promote )
                self.assertEqual( 1, count )
                self.assertEqual( 'File Upload', observed[ 'loader_name' ] )
                self.assertEqual( filename, observed[ 'documents' ][ 0 ].metadata[ 'source' ] )
                self.assertFalse( observed[ 'temporary_path' ].exists( ) )

    def test_loader_failure_cleans_up_temp_files( self ) -> None:
        observed = { }

        class BrokenLoader:
            def load( self, filepath: str ) -> list:
                observed[ 'path' ] = Path( filepath )
                raise RuntimeError( 'Unparseable input' )

        with self.assertRaisesRegex( RuntimeError, 'Unparseable input' ):
            load_uploaded_document( UploadedFile( 'broken.txt', b'contents' ),
                { '.txt': BrokenLoader }, lambda documents, name: 0 )
        self.assertFalse( observed[ 'path' ].exists( ) )

    def test_path_based_loader_uses_path_keyword( self ) -> None:
        observed = { }

        class WordLoader:
            def load( self, path: str ) -> list:
                observed[ 'path' ] = Path( path )
                return [ Document( observed[ 'path' ].read_text( ) ) ]

        count = load_uploaded_document( UploadedFile( 'document.docx', b'test content' ),
            { '.docx': WordLoader }, lambda documents, name: len( documents ) )
        self.assertEqual( 1, count )
        self.assertFalse( observed[ 'path' ].exists( ) )


if __name__ == '__main__':
    unittest.main( )
