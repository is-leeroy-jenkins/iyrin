"""Regression tests for validated AIS Stream subscription inputs."""

import ast
import json
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SourceError(Exception):
    """Represent the application's logged provider exception."""


class FakeSocket:
    """Provide a deterministic AIS Stream connection."""

    def __init__(self) -> None:
        """Initialize a single provider position report."""
        self.subscription = ''
        self.closed = False
        self.frames = [json.dumps({'MessageType': 'SubscriptionConfirmation',
            'Message': {'CompressionEnabled': True}}), json.dumps({
            'MessageType': 'PositionReport',
            'MetaData': {'Latitude': 38.0, 'Longitude': -77.0}})]

    def send(self, payload: str) -> None:
        """Capture the exact subscription sent to the provider."""
        self.subscription = payload

    def recv(self, timeout: float) -> str:
        """Return subscription confirmation followed by a position report."""
        return self.frames.pop(0)

    def close(self) -> None:
        """Close the mock socket using the provider contract."""
        self.closed = True


class AisStreamValidationTests(unittest.TestCase):
    """Validate AIS bounds and the original subscription contract."""

    def setUp(self) -> None:
        """Load the production method without an actual WebSocket connection."""
        tree = ast.parse((ROOT / 'sources.py').read_text(encoding='utf-8'))
        guard = next(node for node in tree.body
                     if isinstance(node, ast.FunctionDef) and node.name == 'throw_if')
        cls = next(node for node in tree.body
                   if isinstance(node, ast.ClassDef) and node.name == 'AisStreamLive')
        method = next(node for node in cls.body
                      if isinstance(node, ast.FunctionDef) and node.name == 'fetch_positions')
        self.socket = FakeSocket()
        namespace = {
            'Any': Any, 'Dict': Dict, 'List': List,
            'Error': SourceError,
            'Logger': lambda: SimpleNamespace(write=lambda exception: None),
            'math': math,
            'json': json,
            'time': __import__('time'),
            'connect': lambda url, open_timeout, compression, close_timeout: self.socket,
        }
        module = ast.fix_missing_locations(ast.Module(
            body=[guard, method], type_ignores=[]))
        exec(compile(module, str(ROOT / 'sources.py'), 'exec'), namespace)
        self.fetch = namespace['fetch_positions']
        self.source = SimpleNamespace(
            api_key='test-key', max_retries=0, retry_delay=0,
            timeout=5, url='wss://example.org', socket=None,
        )

    def test_boundaries_reject_invalid_numbers(self) -> None:
        """Reject invalid message caps, duration and geographic coordinates."""
        invalid = [
            (0.0, 0.0, 2.0, 0, 3.0),
            (0.0, 0.0, 2.0, 10, float('nan')),
            (float('nan'), 0.0, 2.0, 10, 3.0),
            (0.0, 200.0, 2.0, 10, 3.0),
        ]
        for arguments in invalid:
            with self.subTest(arguments=arguments), self.assertRaises(SourceError):
                self.fetch(self.source, *arguments)

    def test_valid_subscription_preserves_unmodified_arguments(self) -> None:
        """Send a bounded subscription and return the received vessel message."""
        messages = self.fetch(self.source, 38.0, -77.0, 2.0, 1, 3.0)
        self.assertEqual(1, len(messages))
        subscription = json.loads(self.socket.subscription)
        self.assertEqual('test-key', subscription['APIKey'])
        self.assertTrue(self.socket.closed)
        self.assertEqual(1, self.source.max_messages)

    def test_missing_subscription_confirmation_fails(self) -> None:
        """Reject a position feed that never acknowledges the subscription."""
        self.socket.frames = [json.dumps({'MessageType': 'PositionReport',
            'MetaData': {'Latitude': 38.0, 'Longitude': -77.0}})]
        self.socket.recv = lambda timeout: (_ for _ in ()).throw(TimeoutError())
        with self.assertRaises(SourceError):
            self.fetch(self.source, 38.0, -77.0, 2.0, 1, 0.01)



if __name__ == '__main__':
    unittest.main()
