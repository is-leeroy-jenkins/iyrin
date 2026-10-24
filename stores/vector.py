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
		throw_if( 'documents', documents )
		throw_if( 'embedder', embedder )
		throw_if( 'collection_name', collection_name )
		throw_if( 'persist_directory', persist_directory )
		self.documents = list( documents )
		self.embedder = embedder
		self.collection_name = collection_name
		self.persist_directory = persist_directory
		Path( self.persist_directory ).mkdir( parents=True, exist_ok=True )
		self.vector_store = Chroma(
			collection_name=self.collection_name,
			embedding_function=self.embedder,
			persist_directory=self.persist_directory )
		ids = vector_document_ids( self.documents )
		self.vector_store.add_documents( documents=self.documents, ids=ids )
		return self.vector_store


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
		throw_if( 'documents', documents )
		throw_if( 'embedder', embedder )
		throw_if( 'index_name', index_name )
		throw_if( 'api_key', api_key )
		self.documents = list( documents )
		self.embedder = embedder
		self.index_name = index_name
		self.namespace = namespace
		self.api_key = api_key

		from langchain_pinecone import PineconeVectorStore
		from pinecone import Pinecone

		self.client = Pinecone( api_key=self.api_key )
		if not self.client.indexes.exists( self.index_name ):
			raise ValueError( f'Pinecone index does not exist: {self.index_name}' )

		index = self.client.index( name=self.index_name )
		self.vector_store = PineconeVectorStore(
			index=index,
			embedding=self.embedder,
			namespace=self.namespace or None )
		ids = vector_document_ids( self.documents )
		self.vector_store.add_documents( documents=self.documents, ids=ids )
		return self.vector_store