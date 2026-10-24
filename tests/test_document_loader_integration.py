"""Integration checks using Iyrin's actual document loader classes.

Run with IYRIN_INTEGRATION_TESTS=1 after installing requirements-runtime.txt.
Tests generate their own disposable documents and need no provider credentials.
"""
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


@unittest.skipUnless( os.environ.get( 'IYRIN_INTEGRATION_TESTS' ) == '1',
    'Set IYRIN_INTEGRATION_TESTS=1 to run installed loader integration tests.' )
class DocumentLoaderIntegrationTests( unittest.TestCase ):
    """Exercise supported formats through the real File Upload pipeline."""

    @classmethod
    def setUpClass( cls ) -> None:
        from loaders import (TextLoader, CsvLoader, PdfLoader, ExcelLoader, WordLoader,
            MarkdownLoader, HtmlLoader, JsonLoader, PowerPointLoader, XmlLoader)
        from upload_documents import load_uploaded_document
        cls.load_uploaded_document = staticmethod( load_uploaded_document )
        cls.loaders = {
            '.txt': TextLoader,
            '.csv': CsvLoader,
            '.xlsx': ExcelLoader,
            '.pdf': PdfLoader,
            '.docx': WordLoader,
            '.pptx': PowerPointLoader,
            '.md': MarkdownLoader,
            '.html': HtmlLoader,
            '.json': JsonLoader,
            '.xml': XmlLoader,
        }

    @staticmethod
    def fixture_bytes( ) -> dict:
        """Produce valid document fixtures entirely in memory."""
        import fitz
        import pandas as pd
        from docx import Document as WordDocument
        from pptx import Presentation

        token = 'IyrinFixtureAlpha'
        word = WordDocument( )
        word.add_paragraph( token )
        word_bytes = io.BytesIO( )
        word.save( word_bytes )

        presentation = Presentation( )
        slide = presentation.slides.add_slide( presentation.slide_layouts[ 6 ] )
        textbox = slide.shapes.add_textbox( 0, 0, presentation.slide_width,
            presentation.slide_height )
        textbox.text_frame.text = token
        presentation_bytes = io.BytesIO( )
        presentation.save( presentation_bytes )

        spreadsheet_bytes = io.BytesIO( )
        pd.DataFrame( [ { 'name': token, 'value': 7 } ] ).to_excel(
            spreadsheet_bytes, index=False )

        pdf = fitz.open( )
        page = pdf.new_page( )
        page.insert_text( (72, 72), token )
        pdf_bytes = pdf.tobytes( )
        pdf.close( )

        return {
            'fixture.txt': token.encode( 'utf-8' ),
            'fixture.csv': f'name,value\\n{token},7\\n'.replace(
                '\\n', '\n' ).encode( 'utf-8' ),
            'fixture.xlsx': spreadsheet_bytes.getvalue( ),
            'fixture.pdf': pdf_bytes,
            'fixture.docx': word_bytes.getvalue( ),
            'fixture.pptx': presentation_bytes.getvalue( ),
            'fixture.md': f'# {token}\n'.encode( 'utf-8' ),
            'fixture.html': f'<html><body><p>{token}</p></body></html>'.encode( 'utf-8' ),
            'fixture.json': json.dumps( { 'name': token } ).encode( 'utf-8' ),
            'fixture.xml': f'<root><name>{token}</name></root>'.encode( 'utf-8' ),
        }

    def test_real_parsers_return_documents_and_preserve_metadata( self ) -> None:
        class UploadedFile:
            def __init__( self, name: str, contents: bytes ) -> None:
                self.name = name
                self.contents = contents

            def getvalue( self ) -> bytes:
                return self.contents

        for name, payload in self.fixture_bytes( ).items( ):
            with self.subTest( name=name ):
                promoted = [ ]

                def promote( documents: list, loader_name: str ) -> int:
                    self.assertEqual( 'File Upload', loader_name )
                    promoted.extend( documents )
                    return len( documents )

                count = self.load_uploaded_document(
                    UploadedFile( name, payload ), self.loaders, promote )
                self.assertGreater( count, 0 )
                self.assertEqual( count, len( promoted ) )
                self.assertTrue( all( isinstance( document.page_content, str )
                    for document in promoted ) )
                self.assertTrue( all( document.metadata.get( 'source' ) == name
                    for document in promoted ) )
                self.assertTrue( any( 'IyrinFixtureAlpha' in document.page_content
                    for document in promoted ) )

    def test_invalid_document_does_not_leave_temporary_file( self ) -> None:
        from upload_documents import load_uploaded_document

        class BrokenFile:
            name = 'invalid.docx'

            def getvalue( self ) -> bytes:
                return b'not a valid word file'

        with self.assertRaises( Exception ):
            load_uploaded_document( BrokenFile( ), { '.docx': self.loaders[ '.docx' ] },
                lambda documents, name: len( documents ) )


if __name__ == '__main__':
    unittest.main( )
