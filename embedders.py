'''
    ******************************************************************************************
      Assembly:                iyrin
      Filename:                embedders.py
      Author:                  Terry D. Eppler
      Created:                 09-08-2026
      Last Modified By:        Terry D. Eppler
      Last Modified On:        09-08-2026
    ******************************************************************************************
    <summary>
        LangChain embedding implementations used by iyrin document workflows.
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations
from pathlib import Path
from typing import Any, List
from boogr import Error, Logger
from hashlib import sha256
from langchain_core.embeddings import Embeddings

def throw_if( name: str, value: object ) -> None:
	"""Validate a required runtime value.

	Purpose:
		Ensures required embedding configuration and input values are present before provider or
		local-model work begins.

	Args:
		name (str): Argument name included in validation errors.
		value (object): Runtime value to validate.

	Returns:
		None: This function validates input and does not return a value.
	"""
	if value is None:
		raise ValueError( f'Argument "{name}" cannot be empty!' )

	if isinstance( value, str ) and not value.strip( ):
		raise ValueError( f'Argument "{name}" cannot be empty!' )

	if isinstance( value, ( list, tuple, dict, set ) ) and len( value ) == 0:
		raise ValueError( f'Argument "{name}" cannot be empty!' )

def chunk_identifier( document: object, position: int ) -> str:
    """Generate a deterministic identifier for a document chunk.

    Purpose:
        Combines the source, ordinal position, and content of a chunk into a stable SHA-256 ID.

    Args:
        document (object): Document-like value containing the source metadata and chunk text.
        position (int): One-based position of the chunk within the source sequence.

    Returns:
        str: Source-scoped, reproducible chunk identifier.
    """
    metadata = document.metadata or { }
    source = str( metadata.get( 'source', '' ) )
    payload = f'{source}\x00{position}\x00{document.page_content}'
    return f'chunk-{sha256( payload.encode( "utf-8" ) ).hexdigest( )}'

def vector_document_ids( documents: list[ object ] ) -> list[ str ]:
    """Resolve unique identifiers for a collection of document chunks.

    Purpose:
        Preserves explicit chunk IDs and generates deterministic IDs for missing entries.
        Duplicate identifiers are rejected before a vector store receives the documents.

    Args:
        documents (list[object]): Documents to identify for vector storage.

    Returns:
        list[str]: Identifiers in the same order as the supplied documents.

    Raises:
        ValueError: Raised when two documents resolve to the same identifier.
    """
    ids = [ ]
    for position, document in enumerate( documents, start=1 ):
        metadata = document.metadata or { }
        identifier = metadata.get( 'chunk_id' )
        ids.append( str( identifier ) if identifier else
            chunk_identifier( document, position ) )
    if len( set( ids ) ) != len( ids ):
        raise ValueError( 'Duplicate chunk identifiers in vector storage request.' )
    return ids

class LocalEmbeddings( Embeddings ):
	"""Local GGUF embedding adapter for LangChain.

	Purpose:
		Loads a local GGUF model using llama-cpp-python and generates text embeddings.
		The model client is initialized lazily and reused across requests.

	Attributes:
		model_path (str): File path to the configured GGUF model.
		client (Any): Loaded llama-cpp-python model client, or None before loading.
		response (object | None): Most recent raw embedding response.
		texts (List[str]): Most recently supplied document texts.
		text (str): Most recently supplied query text.
	"""

	model_path: str
	client: Any
	response: object | None
	texts: List[ str ]
	text: str

	def __init__( self, model_path: str ) -> None:
		"""Initialize the local GGUF embedding adapter.

		Purpose:
			Stores the validated model path and initializes empty runtime state.

		Args:
			model_path (str): Required path to a GGUF model file.

		Returns:
			None: Initializes instance members.
		"""
		throw_if( 'model_path', model_path )
		if not isinstance( model_path, str ):
			raise TypeError( 'model_path must be a string.' )
		self.model_path = model_path
		self.client = None
		self.response = None
		self.texts = [ ]
		self.text = ''

	def load( self ) -> None:
		"""Initialize the configured GGUF model client if necessary.

		Purpose:
			Reuses an existing client or loads the model at the configured path.

		Returns:
			None: Updates the client attribute when necessary.

		Raises:
			FileNotFoundError: Raised when the configured GGUF model does not exist.
		"""
		try:
			if self.client is not None:
				return

			path = Path( self.model_path )
			if not path.is_file( ):
				raise FileNotFoundError( f'Local GGUF model not found: {self.model_path}' )

			from llama_cpp import Llama
			self.client = Llama( model_path=self.model_path, embedding=True, verbose=False )
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'LocalEmbeddings'
			exception.method = 'load( self ) -> None'
			Logger( ).write( exception )
			raise exception from e

	def embed_documents( self, texts: List[ str ] ) -> List[ List[ float ] ]:
		"""Generate vector embeddings for document content.

		Purpose:
			Calls the loaded GGUF embedding client and verifies the output count.

		Args:
			texts (List[str]): Nonempty document texts to embed.

		Returns:
			List[List[float]]: Embedding vectors corresponding to the input texts.

		Raises:
			TypeError: Raised when texts is not a list of strings.
			RuntimeError: Raised when the returned embedding count is inconsistent.
		"""
		try:
			throw_if( 'texts', texts )
			if not isinstance( texts, list ):
				raise TypeError( 'texts must be a list of strings.' )
			self.texts = texts
			values: List[ str ] = [ ]
			for text in texts:
				throw_if( 'text', text )
				if not isinstance( text, str ):
					raise TypeError( 'Argument "texts" must contain only strings.' )
				values.append( text )
	
			self.load( )
			self.response = self.client.create_embedding( values )
			if isinstance( self.response, dict ) and 'data' in self.response:
				vectors = [ item[ 'embedding' ] for item in self.response[ 'data' ] ]
			else:
				vectors = self.response
	
			if not isinstance( vectors, list ) or len( vectors ) != len( values ):
				raise RuntimeError( 'Local GGUF embedding count does not match the input count.' )
	
			return vectors
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'LocalEmbeddings'
			exception.method = 'embed_documents( self, texts: List[ str ] ) -> List[ List[ float ] ]'
			Logger( ).write( exception )
			raise exception from e

	def embed_query( self, text: str ) -> List[ float ]:
		"""Generate a single query embedding.

		Purpose:
			Uses the document embedding implementation for a single query.

		Args:
			text (str): Nonempty query to embed.

		Returns:
			List[float]: The embedding for the supplied query.
		"""
		try:
			throw_if( 'text', text )
			if not isinstance( text, str ):
				raise TypeError( 'Argument "text" must be a string.' )
			self.text = text
			return self.embed_documents( [ self.text ] )[ 0 ]
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'LocalEmbeddings'
			exception.method = 'embed_query( self, text: str ) -> List[ float ]'
			Logger( ).write( exception )
			raise exception from e

class EmbeddingFactory( ):
	"""Factory for supported LangChain embedding providers.

	Purpose:
		Creates OpenAI, Google, Mistral, Hugging Face, or local GGUF embedding adapters.

	Attributes:
		provider (str): Selected embedding provider.
		model (str): Selected provider model identifier.
		model_path (str): Local GGUF model path, if applicable.
	"""
	provider: str
	model: str
	model_path: str

	def __init__( self ) -> None:
		"""Initialize embedding provider selection state.

		Purpose:
			Sets empty provider, model, and local-model configuration attributes.

		Returns:
			None: Initializes instance members.
		"""
		self.provider = ''
		self.model = ''
		self.model_path = ''

	def create( self, provider: str, model: str, model_path: str = '' ) -> Embeddings:
		"""Construct a configured embedding provider wrapper.

		Purpose:
			Dispatches to the requested provider without loading unrelated provider SDKs.

		Args:
			provider (str): Provider name used to choose the implementation.
			model (str): Model identifier for the selected provider.
			model_path (str): Optional GGUF model file path for the local provider.

		Returns:
			Embeddings: LangChain-compatible embedding implementation.

		Raises:
			ValueError: Raised for unsupported providers or missing local-model paths.
		"""
		try:
			throw_if( 'provider', provider )
			throw_if( 'model', model )
			if not isinstance( provider, str ) or not isinstance( model, str ):
				raise TypeError( 'provider and model must be strings.' )
			if not isinstance( model_path, str ):
				raise TypeError( 'model_path must be a string.' )
			self.provider = provider
			self.model = model
			self.model_path = model_path
			if self.provider == 'OpenAI':
				from langchain_openai import OpenAIEmbeddings
				return OpenAIEmbeddings( model=self.model )
	
			if self.provider == 'Google Generative AI':
				from langchain_google_genai import GoogleGenerativeAIEmbeddings
				return GoogleGenerativeAIEmbeddings( model=self.model )
	
			if self.provider == 'Mistral AI':
				from langchain_mistralai import MistralAIEmbeddings
				return MistralAIEmbeddings( model=self.model )
	
			if self.provider == 'Hugging Face':
				from langchain_huggingface import HuggingFaceEmbeddings
				return HuggingFaceEmbeddings( model_name=self.model )
	
			if self.provider == 'Local GGUF':
				throw_if( 'model_path', self.model_path )
				return LocalEmbeddings( model_path=self.model_path )
	
			raise ValueError( f'Unsupported embedding provider: {self.provider}' )
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'EmbeddingFactory'
			exception.method = "create( self, provider: str, model: str, model_path: str='' ) -> Embeddings"
			Logger( ).write( exception )
			raise exception from e
		