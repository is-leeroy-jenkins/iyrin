"""Credential-free PineconeStore integration-contract tests."""
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch


ROOT = Path( __file__ ).resolve( ).parents[ 1 ]


class PineconeStoreContractTests( unittest.TestCase ):
    """Exercise production PineconeStore against instrumented SDK clients."""

    @classmethod
    def setUpClass( cls ) -> None:
        cls.vector_source = (ROOT / 'stores' / 'vector.py').read_text(
            encoding='utf-8' )

    def create_store( self, index_exists: bool=True ):
        """Construct a production store with mocked provider SDK modules."""
        import ast
        from chunk_ids import vector_document_ids

        module = ast.parse( self.vector_source )
        store_class = next( node for node in module.body if isinstance( node, ast.ClassDef )
            and node.name == 'PineconeStore' )
        throw_if = next( node for node in module.body if isinstance( node, ast.FunctionDef )
            and node.name == 'throw_if' )
        isolated = ast.Module( body=[ throw_if, store_class ], type_ignores=[ ] )
        environment = { 'Any': object, 'List': list, 'Document': object,
            'Embeddings': object, 'vector_document_ids': vector_document_ids }
        exec( compile( ast.fix_missing_locations( isolated ), '<vector>', 'exec' ),
            environment )
        store = environment[ 'PineconeStore' ]( )
        sdk = MagicMock( )
        sdk.indexes.exists.return_value = index_exists
        pinecone_module = ModuleType( 'pinecone' )
        pinecone_module.Pinecone = MagicMock( return_value=sdk )
        langchain_module = ModuleType( 'langchain_pinecone' )
        langchain_module.PineconeVectorStore = MagicMock( )
        return store, sdk, pinecone_module, langchain_module

    def test_index_lookup_namespace_and_explicit_ids( self ) -> None:
        store, sdk, pinecone_module, langchain_module = self.create_store( )
        documents = [ SimpleNamespace( page_content='first',
            metadata={ 'source': 'a', 'chunk_id': 'a-001' } ) ]
        embedder = object( )
        with patch.dict( sys.modules, { 'pinecone': pinecone_module,
                'langchain_pinecone': langchain_module } ):
            result = store.create( documents, embedder, 'sample-index',
                'team-a', 'test-api-key' )
        pinecone_module.Pinecone.assert_called_once_with( api_key='test-api-key' )
        sdk.indexes.exists.assert_called_once_with( 'sample-index' )
        sdk.index.assert_called_once_with( name='sample-index' )
        langchain_module.PineconeVectorStore.assert_called_once_with(
            index=sdk.index.return_value, embedding=embedder, namespace='team-a' )
        result.add_documents.assert_called_once_with(
            documents=documents, ids=[ 'a-001' ] )

    def test_empty_namespace_uses_default_namespace( self ) -> None:
        store, sdk, pinecone_module, langchain_module = self.create_store( )
        documents = [ SimpleNamespace( page_content='first',
            metadata={ 'source': 'a' } ) ]
        with patch.dict( sys.modules, { 'pinecone': pinecone_module,
                'langchain_pinecone': langchain_module } ):
            store.create( documents, object( ), 'sample-index', '', 'test-api-key' )
        self.assertIsNone( langchain_module.PineconeVectorStore.call_args.kwargs[
            'namespace' ] )
        first_ids = langchain_module.PineconeVectorStore.return_value.add_documents.call_args.kwargs[
            'ids' ]
        self.assertEqual( 1, len( first_ids ) )
        self.assertTrue( first_ids[ 0 ].startswith( 'chunk-' ) )

    def test_missing_index_prevents_write( self ) -> None:
        store, sdk, pinecone_module, langchain_module = self.create_store(
            index_exists=False )
        documents = [ SimpleNamespace( page_content='first', metadata={ } ) ]
        with patch.dict( sys.modules, { 'pinecone': pinecone_module,
                'langchain_pinecone': langchain_module } ):
            with self.assertRaisesRegex( ValueError, 'Pinecone index does not exist' ):
                store.create( documents, object( ), 'missing-index',
                    'team-a', 'test-api-key' )
        sdk.index.assert_not_called( )
        langchain_module.PineconeVectorStore.assert_not_called( )

    def test_duplicate_ids_do_not_write( self ) -> None:
        store, sdk, pinecone_module, langchain_module = self.create_store( )
        documents = [ SimpleNamespace( page_content=str( index ),
            metadata={ 'chunk_id': 'duplicate' } ) for index in range( 2 ) ]
        with patch.dict( sys.modules, { 'pinecone': pinecone_module,
                'langchain_pinecone': langchain_module } ):
            with self.assertRaisesRegex( ValueError, 'Duplicate chunk identifiers' ):
                store.create( documents, object( ), 'sample-index',
                    'team-a', 'test-api-key' )
        langchain_module.PineconeVectorStore.return_value.add_documents.assert_not_called( )

    def test_provider_error_is_not_suppressed( self ) -> None:
        store, sdk, pinecone_module, langchain_module = self.create_store( )
        langchain_module.PineconeVectorStore.return_value.add_documents.side_effect = RuntimeError(
            'remote write failed' )
        documents = [ SimpleNamespace( page_content='first',
            metadata={ 'chunk_id': 'a-001' } ) ]
        with patch.dict( sys.modules, { 'pinecone': pinecone_module,
                'langchain_pinecone': langchain_module } ):
            with self.assertRaisesRegex( RuntimeError, 'remote write failed' ):
                store.create( documents, object( ), 'sample-index',
                    'team-a', 'test-api-key' )


if __name__ == '__main__':
    unittest.main( )
