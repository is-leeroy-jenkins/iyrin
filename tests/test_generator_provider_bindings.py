"""Regression checks for distinct provider wrapper and SDK client bindings.

Purpose:
    Keep provider wrapper names separate from imported SDK constructors.
"""

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class GeneratorProviderBindingTests(unittest.TestCase):
    """Verify provider names, call targets, and public method naming."""

    @classmethod
    def setUpClass(cls) -> None:
        """Parse the production generator source once for the test class."""
        cls.tree = ast.parse((ROOT / 'generators.py').read_text(encoding='utf-8'))

    def test_provider_sdk_aliases_do_not_shadow_classes(self) -> None:
        """Reject imports that overwrite or are overwritten by wrappers."""
        classes = {node.name for node in self.tree.body
                   if isinstance(node, ast.ClassDef)}
        aliases = {alias.asname or alias.name for node in self.tree.body
                   if isinstance(node, (ast.Import, ast.ImportFrom))
                   for alias in node.names}
        self.assertFalse(classes & aliases)

    def test_claude_fetch_constructs_anthropic_client(self) -> None:
        """Verify Claude.fetch constructs the SDK client, not its own wrapper."""
        claude = next(node for node in self.tree.body
                      if isinstance(node, ast.ClassDef) and node.name == 'Claude')
        fetch = next(node for node in claude.body
                     if isinstance(node, ast.FunctionDef) and node.name == 'fetch')
        constructors = {node.func.id for node in ast.walk(fetch)
                        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        self.assertIn('AnthropicClient', constructors)
        self.assertNotIn('Claude', constructors)

    def test_all_generator_methods_follow_public_naming(self) -> None:
        """Enforce the no-leading-underscore convention for ordinary methods."""
        invalid = [(cls.name, method.name) for cls in self.tree.body
                   if isinstance(cls, ast.ClassDef)
                   for method in cls.body
                   if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and method.name.startswith('_')
                   and not (method.name.startswith('__') and method.name.endswith('__'))]
        self.assertEqual([], invalid)


if __name__ == '__main__':
    unittest.main()
