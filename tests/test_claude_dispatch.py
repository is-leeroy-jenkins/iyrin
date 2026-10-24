"""Regression tests for the Claude generation execution path."""
import ast
from pathlib import Path
import unittest


APP_PATH = Path( __file__ ).resolve( ).parents[ 1 ] / 'app.py'


class ClaudeDispatchTests( unittest.TestCase ):
    """Ensure the Claude controls invoke the provider and publish its response."""

    @classmethod
    def setUpClass( cls ) -> None:
        cls.source = APP_PATH.read_text( encoding='utf-8' )
        cls.syntax = ast.parse( cls.source )

    def test_claude_generator_imported( self ) -> None:
        imports = [ node for node in ast.walk( self.syntax )
            if isinstance( node, ast.ImportFrom ) and node.module == 'generators' ]
        self.assertTrue( any( 'Claude' in { alias.name for alias in node.names }
            for node in imports ) )

    def test_claude_submit_invokes_and_promotes_response( self ) -> None:
        branches = [ node for node in ast.walk( self.syntax )
            if isinstance( node, ast.If ) and isinstance( node.test, ast.Name )
            and node.test.id == 'claude_submit' ]
        self.assertEqual( 1, len( branches ) )
        calls = [ node.func.id for node in ast.walk( branches[ 0 ] )
            if isinstance( node, ast.Call ) and isinstance( node.func, ast.Name ) ]
        self.assertIn( 'Claude', calls )
        self.assertIn( 'invoke_provider', calls )
        self.assertIn( '_promote_generation_result', calls )

    def test_claude_request_carries_all_existing_controls( self ) -> None:
        branch = next( node for node in ast.walk( self.syntax )
            if isinstance( node, ast.If ) and isinstance( node.test, ast.Name )
            and node.test.id == 'claude_submit' )
        keys = { key.value for node in ast.walk( branch ) if isinstance( node, ast.Dict )
            for key in node.keys if isinstance( key, ast.Constant )
            and isinstance( key.value, str ) }
        self.assertTrue( {
            'model', 'temperature', 'max_tokens', 'top_p', 'top_k', 'system',
            'stop_sequences', 'thinking', 'thinking_budget', 'web_search',
            'search_domains', 'blocked_domains',
        } <= keys )

    def test_low_budget_is_guarded_before_budget_widget( self ) -> None:
        self.assertIn( 'if claude_thinking and int( claude_max_tokens ) <= 1024:', self.source )
        self.assertIn( 'Thinking Budget must be less than Max Tokens.', self.source )


if __name__ == '__main__':
    unittest.main( )
