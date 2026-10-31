"""Regression checks for multi-format File Upload processing."""
import ast
from pathlib import Path
import unittest


SOURCE = (Path( __file__ ).resolve( ).parents[ 1 ] / 'app.py').read_text(
    encoding='utf-8' )
TREE = ast.parse( SOURCE )


class FileUploadTests( unittest.TestCase ):
    def test_document_extensions_have_loader_dispatch( self ) -> None:
        start = SOURCE.index( "with st.expander( label='Document Processing'" )
        end = SOURCE.index( "st.subheader( 'Excel / CSV' )", start )
        section = SOURCE[ start:end ]
        for extension in ( '.txt', '.csv', '.xlsx', '.xls', '.pdf', '.docx',
                '.pptx', '.md', '.html', '.htm', '.json', '.xml' ):
            with self.subTest( extension=extension ):
                self.assertIn( f"'{extension}'", section )

    def test_shared_document_pipeline_is_connected( self ) -> None:
        start = SOURCE.index( "with st.expander( label='Document Processing'" )
        end = SOURCE.index( "st.subheader( 'Excel / CSV' )", start )
        section = SOURCE[ start:end ]
        self.assertIn( 'load_uploaded_document( ', section )
        self.assertIn( 'promote_loader_documents )', section )
        for method in ( 'render_document_processing_controls', 'render_loading_tabs' ):
            self.assertIn( method + '( ', section )

    def test_geocoding_upload_workflow_is_preserved( self ) -> None:
        self.assertIn( "key='data_upload_enrich'", SOURCE )
        self.assertIn( "key='data_upload_download'", SOURCE )
        self.assertIn( "key='file_upload_document'", SOURCE )

    def test_temp_files_are_cleanup_scoped( self ) -> None:
        helper = (Path( __file__ ).resolve( ).parents[ 1 ] / 'upload_documents.py').read_text( encoding='utf-8' )
        self.assertIn( 'with TemporaryDirectory( ) as directory:', helper )
        self.assertIn( "document_file.getvalue( )", helper )


if __name__ == '__main__':
    unittest.main( )
