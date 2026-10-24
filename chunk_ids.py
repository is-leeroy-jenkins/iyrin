"""Deterministic, source-scoped identifiers for document chunks."""
from hashlib import sha256


def chunk_identifier( document, position: int ) -> str:
    """Return a stable ID for a chunk's source, content, and ordinal position."""
    metadata = document.metadata or { }
    source = str( metadata.get( 'source', '' ) )
    payload = f'{source}\x00{position}\x00{document.page_content}'
    return f'chunk-{sha256( payload.encode( "utf-8" ) ).hexdigest( )}'


def vector_document_ids( documents: list ) -> list[ str ]:
    """Preserve explicit IDs and derive stable IDs when none are provided."""
    ids = [ ]
    for position, document in enumerate( documents, start=1 ):
        metadata = document.metadata or { }
        identifier = metadata.get( 'chunk_id' )
        ids.append( str( identifier ) if identifier else
            chunk_identifier( document, position ) )
    if len( set( ids ) ) != len( ids ):
        raise ValueError( 'Duplicate chunk identifiers in vector storage request.' )
    return ids
