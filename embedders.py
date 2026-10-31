'''
    ******************************************************************************************
      Assembly:                Iyr
      Filename:                embedders.py
      Author:                  Terry D. Eppler
      Created:                 09-08-2026
      Last Modified By:        Terry D. Eppler
      Last Modified On:        09-08-2026
    ******************************************************************************************
    <summary>
        LangChain embedding implementations used by Iyr document workflows.
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations
from pathlib import Path
from typing import Any, List
from boogr import Error, Logger

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


class LocalGGUFEmbeddings( Embeddings ):
	"""LangChain-compatible local GGUF embedding implementation."""

	model_path: str
	client: Any
	response: object | None

	def __init__( self, model_path: str ) -> None:
		"""Initialize the local GGUF embedding implementation."""
		self.model_path = model_path
		self.client = None
		self.response = None

	def load( self ) -> None:
		"""Load the configured local GGUF model once."""
		if self.client is not None:
			return

		path = Path( self.model_path )
		if not path.is_file( ):
			raise FileNotFoundError( f'Local GGUF model not found: {self.model_path}' )

		from llama_cpp import Llama
		self.client = Llama( model_path=self.model_path, embedding=True, verbose=False )

	def embed_documents( self, texts: List[ str ] ) -> List[ List[ float ] ]:
		"""Create embeddings for document text."""
		throw_if( 'texts', texts )
		try:
			values: List[ str ] = [ ]
			for text in texts:
				throw_if( 'text', text )
				if not isinstance( text, str ):
					raise TypeError( 'Argument "texts" must contain only strings.' )
				values.append( text.strip( ) )
	
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
			raise exception

	def embed_query( self, text: str ) -> List[ float ]:
		"""Create an embedding for query text."""
		throw_if( 'text', text )
		try:
			if not isinstance( text, str ):
				raise TypeError( 'Argument "text" must be a string.' )
			return self.embed_documents( [ text ] )[ 0 ]
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'LocalEmbeddings'
			exception.method = 'embed_query( self, text: str ) -> List[ float ]'
			Logger( ).write( exception )
			raise exception


class EmbeddingFactory( ):
	"""Factory for Iyr's supported LangChain embedding implementations."""

	provider: str
	model: str
	model_path: str

	def __init__( self ) -> None:
		"""Initialize embedding provider state."""
		self.provider = ''
		self.model = ''
		self.model_path = ''

	def create( self, provider: str, model: str, model_path: str = '' ) -> Embeddings:
		"""Create the selected LangChain embedding implementation."""
		throw_if( 'provider', provider )
		throw_if( 'model', model )
		try:
			self.provider = provider
			self.model = model
			self.model_path = model_path
	
			if self.provider == 'OpenAI':
				throw_if( 'model', self.model )
				from langchain_openai import OpenAIEmbeddings
				return OpenAIEmbeddings( model=self.model )
	
			if self.provider == 'Google Generative AI':
				throw_if( 'model', self.model )
				from langchain_google_genai import GoogleGenerativeAIEmbeddings
				return GoogleGenerativeAIEmbeddings( model=self.model )
	
			if self.provider == 'Mistral AI':
				throw_if( 'model', self.model )
				from langchain_mistralai import MistralAIEmbeddings
				return MistralAIEmbeddings( model=self.model )
	
			if self.provider == 'Hugging Face':
				throw_if( 'model', self.model )
				from langchain_huggingface import HuggingFaceEmbeddings
				return HuggingFaceEmbeddings( model_name=self.model )
	
			if self.provider == 'Local GGUF':
				throw_if( 'model_path', self.model_path )
				return LocalGGUFEmbeddings( model_path=self.model_path )
	
			raise ValueError( f'Unsupported embedding provider: {self.provider}' )
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'EmbeddingFactory'
			exception.method = 'create( self, **args ) -> Embeddings'
			Logger( ).write( exception )
			raise exception
		