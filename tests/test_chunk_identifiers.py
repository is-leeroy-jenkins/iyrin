"""Regression coverage for deterministic chunk IDs and vector-store routing."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

from chunk_ids import chunk_identifier, vector_document_ids


ROOT = Path( __file__ ).resolve( ).parents[ 1 ]


class ChunkIdentifierTests( unittest.TestCase ):
    def test_same_source_content_and_position_retries_identically( self ) -> None:
        document = SimpleNamespace( page_content='First chunk',
            metadata={ 'source': 'one.txt' } )
        self.assertEqual( chunk_identifier( document, 1 ),
            chunk_identifier( document, 1 ) )

    def test_different_sources_do_not_collide( self ) -> None:
        first = SimpleNamespace( page_content='Same text',
            metadata={ 'source': 'one.txt' } )
        second = SimpleNamespace( page_content='Same text',
            metadata={ 'source': 'two.txt' } )
        self.assertNotEqual( chunk_identifier( first, 1 ),
            chunk_identifier( second, 1 ) )

    def test_modified_content_and_position_have_distinct_ids( self ) -> None:
        first = SimpleNamespace( page_content='alpha',
            metadata={ 'source': 'one.txt' } )
        second = SimpleNamespace( page_content='beta',
            metadata={ 'source': 'one.txt' } )
        self.assertNotEqual( chunk_identifier( first, 1 ),
            chunk_identifier( second, 1 ) )
        self.assertNotEqual( chunk_identifier( first, 1 ),
            chunk_identifier( first, 2 ) )

    def test_explicit_metadata_id_is_preserved( self ) -> None:
        doc = SimpleNamespace( page_content='content',
            metadata={ 'source': 'one.txt', 'chunk_id': 'existing-001' } )
        self.assertEqual( [ 'existing-001' ], vector_document_ids( [ doc ] ) )

    def test_automatic_fallback_ids_are_stable( self ) -> None:
        docs = [ SimpleNamespace( page_content='alpha', metadata={ 'source': 'a' } ),
            SimpleNamespace( page_content='alpha', metadata={ 'source': 'b' } ) ]
        first = vector_document_ids( docs )
        self.assertEqual( first, vector_document_ids( docs ) )
        self.assertEqual( 2, len( set( first ) ) )

    def test_duplicate_ids_are_rejected( self ) -> None:
        docs = [ SimpleNamespace( page_content=str( i ),
            metadata={ 'chunk_id': 'duplicate' } ) for i in range( 2 ) ]
        with self.assertRaisesRegex( ValueError, 'Duplicate chunk identifiers' ):
            vector_document_ids( docs )

    def test_pipeline_and_both_backends_use_shared_identifiers( self ) -> None:
        pipeline = (ROOT / 'pipelines.py').read_text( encoding='utf-8' )
        storage = (ROOT / 'stores' / 'vector.py').read_text( encoding='utf-8' )
        self.assertIn( "document.metadata[ 'chunk_id' ] = chunk_identifier( document, index )",
            pipeline )
        self.assertEqual( 2, storage.count( 'ids = vector_document_ids( self.documents )' ) )
        ast.parse( pipeline )
        ast.parse( storage )


if __name__ == '__main__':
    unittest.main( )
