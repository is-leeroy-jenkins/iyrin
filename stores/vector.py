'''
    ******************************************************************************************
      Assembly:                Iyr
      Filename:                vector.py
      Author:                  Terry D. Eppler
      Created:                 09-08-2026
      Last Modified By:        Terry D. Eppler
      Last Modified On:        09-08-2026
    ******************************************************************************************
    <summary>
        LangChain vector-storage implementations for Iyr document chunks.
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations
from chunk_ids import vector_document_ids
from pathlib import Path
from typing import Any, List
from boogr import Error, Logger

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings


def throw_if( name: str, value: object ) -> None:
	"""Validate a required runtime value."""
	if value is None:
		raise ValueError( f'Argument "{name}" cannot be empty!' )
	if isinstance( value, str ) and not value.strip( ):
		raise ValueError( f'Argument "{name}" cannot be empty!' )
	if isinstance( value, ( list, tuple, dict, set ) ) and len( value ) == 0:
		raise ValueError( f'Argument "{name}" cannot be empty!' )

class ChromaStore( ):
	"""Persistent local Chroma vector-store wrapper."""

	def __init__( self ) -> None:
		"""Initialize Chroma storage state."""
		self.documents: List[ Document ] = [ ]
		self.embedder: Embeddings | None = None
		self.collection_name = ''
		self.persist_directory = ''
		self.vector_store: Chroma | None = None

	def create( self, documents: List[ Document ], embedder: Embeddings,
		collection_name: str, persist_directory: str ) -> Chroma:
		"""Add documents to a persistent Chroma collection without deleting existing records."""
		try:
			throw_if( 'documents', documents )
			throw_if( 'embedder', embedder )
			throw_if( 'collection_name', collection_name )
			throw_if( 'persist_directory', persist_directory )
			if not isinstance( documents, list ) or not all(
					isinstance( document, Document ) for document in documents ):
				raise TypeError( 'documents must be a list of LangChain Documents.' )
			if not isinstance( embedder, Embeddings ):
				raise TypeError( 'embedder must implement LangChain Embeddings.' )
			if not isinstance( collection_name, str ) or not isinstance( persist_directory, str ):
				raise TypeError( 'collection_name and persist_directory must be strings.' )
			self.documents = documents
			self.embedder = embedder
			self.collection_name = collection_name
			self.persist_directory = persist_directory
			ids = vector_document_ids( self.documents )
			Path( self.persist_directory ).mkdir( parents=True, exist_ok=True )
			store = Chroma(
				collection_name=self.collection_name,
				embedding_function=self.embedder,
				persist_directory=self.persist_directory )
			store.add_documents( documents=self.documents, ids=ids )
			self.vector_store = store
			return self.vector_store
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'ChromaStore'
			exception.method = 'create( self, documents, embedder, collection_name, persist_directory ) -> Chroma'
			Logger( ).write( exception )
			raise exception from e


class PineconeStore( ):
	"""Managed Pinecone vector-store wrapper."""

	def __init__( self ) -> None:
		"""Initialize Pinecone storage state without importing Pinecone."""
		self.documents: List[ Document ] = [ ]
		self.embedder: Embeddings | None = None
		self.index_name = ''
		self.namespace = ''
		self.api_key = ''
		self.client: Any = None
		self.vector_store: Any = None

	def create( self, documents: List[ Document ], embedder: Embeddings, index_name: str,
		namespace: str, api_key: str ) -> Any:
		"""Populate an existing Pinecone index."""
		try:
			throw_if( 'documents', documents )
			throw_if( 'embedder', embedder )
			throw_if( 'index_name', index_name )
			throw_if( 'api_key', api_key )
			if not isinstance( documents, list ) or not all(
					isinstance( document, Document ) for document in documents ):
				raise TypeError( 'documents must be a list of LangChain Documents.' )
			if not isinstance( embedder, Embeddings ):
				raise TypeError( 'embedder must implement LangChain Embeddings.' )
			if not isinstance( index_name, str ) or not isinstance( api_key, str ):
				raise TypeError( 'index_name and api_key must be strings.' )
			if not isinstance( namespace, str ):
				raise TypeError( 'namespace must be a string; empty is allowed.' )
			self.documents = documents
			self.embedder = embedder
			self.index_name = index_name
			self.namespace = namespace
			self.api_key = api_key
			ids = vector_document_ids( self.documents )

			from langchain_pinecone import PineconeVectorStore
			from pinecone import Pinecone

			client = Pinecone( api_key=self.api_key )
			if not client.indexes.exists( self.index_name ):
				raise ValueError( f'Pinecone index does not exist: {self.index_name}' )

			index = client.index( name=self.index_name )
			store = PineconeVectorStore(
				index=index,
				embedding=self.embedder,
				namespace=self.namespace or None )
			store.add_documents( documents=self.documents, ids=ids )
			self.client = client
			self.vector_store = store
			return self.vector_store
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'PineconeStore'
			exception.method = 'create( self, documents, embedder, index_name, namespace, api_key ) -> Any'
			Logger( ).write( exception )
			raise exception from e