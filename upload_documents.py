"""File-upload execution boundary shared by Streamlit and regression tests."""
from pathlib import Path
from tempfile import TemporaryDirectory


def load_uploaded_document( document_file, loaders: dict, promote_loader_documents ) -> int:
    """Load an uploaded document and promote its content into processing state."""
    extension = Path( document_file.name ).suffix.lower( )
    loader_type = loaders[ extension ]
    with TemporaryDirectory( ) as directory:
        path = Path( directory ) / f'uploaded{extension}'
        path.write_bytes( document_file.getvalue( ) )
        loader = loader_type( )
        if extension in ( '.xlsx', '.xls', '.docx', '.pptx', '.md', '.html', '.htm' ):
            documents = loader.load( path=str( path ) )
        elif extension == '.json':
            documents = loader.load( filepath=str( path ), is_text=False )
        else:
            documents = loader.load( filepath=str( path ) )
        for document in documents:
            document.metadata[ 'source' ] = document_file.name
        return promote_loader_documents( documents, 'File Upload' )
