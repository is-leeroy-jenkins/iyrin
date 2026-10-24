"""Local integration tests for chunking, embedding and persistent Chroma storage.

Run with IYRIN_INTEGRATION_TESTS=1 after installing runtime dependencies.
No cloud credentials, model downloads or network calls are required.
"""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


@unittest.skipUnless( os.environ.get( 'IYRIN_INTEGRATION_TESTS' ) == '1',
    'Set IYRIN_INTEGRATION_TESTS=1 to run vector integration tests.' )
class VectorPipelineIntegrationTests( unittest.TestCase ):
    """Exercise the production pipeline using deterministic local embeddings."""

    @classmethod
    def setUpClass( cls ) -> None:
        from langchain_core.documents import Document
        from langchain_core.embeddings import Embeddings
        import pipelines
        from langchain_chroma import Chroma

        class LocalEmbeddings( Embeddings ):
            def embed_documents( self, texts: list[ str ] ) -> list[ list[ float ] ]:
                return [ self.embed_query( text ) for text in texts ]

            def embed_query( self, text: str ) -> list[ float ]:
                return [ float( len( text ) ), float( text.count( 'a' ) ),
                    float( text.count( 'e' ) ) ]

        cls.Document = Document
        cls.Chroma = Chroma
        cls.pipelines = pipelines
        cls.LocalEmbeddings = LocalEmbeddings

    def test_chunk_embed_store_and_reopen( self ) -> None:
        embedder = self.LocalEmbeddings( )
        with TemporaryDirectory( ) as directory:
            documents = [ self.Document( page_content='alpha beta gamma ' * 12,
                metadata={ 'source': 'first.txt' } ) ]
            chunks = self.pipelines.chunk_documents( documents, 80, 10 )
            self.assertGreater( len( chunks ), 1 )
            self.assertTrue( all( document.metadata.get( 'source' ) == 'first.txt'
                for document in chunks ) )
            self.assertTrue( all( document.metadata.get( 'chunk_id' ) for document in chunks ) )

            factory = type( 'Factory', ( ), {
                'create': lambda self, provider, model, model_path: embedder } )
            with patch.object( self.pipelines, 'EmbeddingFactory', factory ):
                returned_embedder, vectors = self.pipelines.create_embeddings(
                    chunks, 'Local', 'Deterministic', '' )
            self.assertIs( embedder, returned_embedder )
            self.assertEqual( len( chunks ), len( vectors ) )
            self.assertEqual( { 3 }, { len( vector ) for vector in vectors } )

            store = self.pipelines.store_documents(
                chunks, embedder, 'Chroma', 'iyrin-integration',
                directory, '' )
            self.assertEqual( len( chunks ), store._collection.count( ) )

            reopened = self.Chroma( collection_name='iyrin-integration',
                persist_directory=directory, embedding_function=embedder )
            self.assertEqual( len( chunks ), reopened._collection.count( ) )
            matches = reopened.similarity_search( 'alpha', k=1 )
            self.assertTrue( matches )
            self.assertEqual( 'first.txt', matches[ 0 ].metadata[ 'source' ] )

    def test_second_store_keeps_existing_documents( self ) -> None:
        embedder = self.LocalEmbeddings( )
        with TemporaryDirectory( ) as directory:
            first = [ self.Document( page_content='first record',
                metadata={ 'source': 'first.txt', 'chunk_id': 'first-001' } ) ]
            second = [ self.Document( page_content='second record',
                metadata={ 'source': 'second.txt', 'chunk_id': 'second-001' } ) ]

            self.pipelines.store_documents(
                first, embedder, 'Chroma', 'iyrin-integration', directory, '' )
            self.pipelines.store_documents(
                second, embedder, 'Chroma', 'iyrin-integration', directory, '' )

            reopened = self.Chroma( collection_name='iyrin-integration',
                persist_directory=directory, embedding_function=embedder )
            self.assertEqual( 2, reopened._collection.count( ) )
            sources = { item[ 'source' ] for item in reopened.get( )[
                'metadatas' ] }
            self.assertEqual( { 'first.txt', 'second.txt' }, sources )


if __name__ == '__main__':
    unittest.main( )
