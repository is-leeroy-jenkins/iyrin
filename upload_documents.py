'''
  ******************************************************************************************
      Assembly:                Iyrin
      Filename:                rates.py
      Author:                  Terry D. Eppler
      Created:                 05-31-2022

      Last Modified By:        Terry D. Eppler
      Last Modified On:        05-01-2025
  ******************************************************************************************
  <copyright file="upload_documents.py" company="Terry D. Eppler">

		upload_documents.py
	    Copyright ©  2025  Terry Eppler

     Permission is hereby granted, free of charge, to any person obtaining a copy
     of this software and associated documentation files (the “Software”),
     to deal in the Software without restriction,
     including without limitation the rights to use,
     copy, modify, merge, publish, distribute, sublicense,
     and/or sell copies of the Software,
     and to permit persons to whom the Software is furnished to do so,
     subject to the following conditions:

     The above copyright notice and this permission notice shall be included in all
     copies or substantial portions of the Software.

     THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
     INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
     FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT.
     IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
     DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
     ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
     DEALINGS IN THE SOFTWARE.

     You can contact me at:  terryeppler@gmail.com or eppler.terry@epa.gov

  </copyright>
  <summary>
    File-upload execution boundary shared by Streamlit and regression tests.
  </summary>
  ******************************************************************************************
'''
from pathlib import Path
from tempfile import TemporaryDirectory


def load_uploaded_document( document_file, loaders: dict,
                            promote_loader_documents ) -> int:
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
