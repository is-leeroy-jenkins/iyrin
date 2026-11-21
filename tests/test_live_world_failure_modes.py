"""Regression tests for OpenSky authorization, AIS configuration, and Overpass retries.

Purpose:
    Validate the production Live World provider functions with controlled HTTP,
    clock, and Streamlit state dependencies, without contacting external providers.
"""
from __future__ import annotations

import ast
import datetime as dt
from email.utils import format_datetime, parsedate_to_datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import Mock
import unittest

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]


class WrappedProviderError(Exception):
    """Represent the application's exception wrapper in isolated provider tests.

    Attributes:
        error (Exception): Original provider exception.
        module (str): Module name assigned by the provider.
        cause (str): Provider class assigned by the provider.
        method (str): Provider method assigned by the provider.
    """

    def __init__(self, error: Exception) -> None:
        """Retain the original exception for assertions.

        Args:
            error (Exception): Original exception.

        Returns:
            None: Initializes wrapper state.
        """
        super().__init__(str(error))
        self.error = error
        self.module = ''
        self.cause = ''
        self.method = ''


class FakeClock:
    """Provide a deterministic monotonic clock without sleeping.

    Attributes:
        now (float): Current simulated time in seconds.
        sleeps (List[float]): Backoff delays requested by the provider.
    """

    def __init__(self) -> None:
        """Initialize the fake clock and delay history."""
        self.now = 0.0
        self.sleeps: List[float] = []

    def monotonic(self) -> float:
        """Return the simulated monotonic time.

        Returns:
            float: Current simulated time.
        """
        return self.now

    def sleep(self, duration: float) -> None:
        """Advance time by a requested backoff delay.

        Args:
            duration (float): Delay in seconds.

        Returns:
            None: Advances the fake clock.
        """
        self.sleeps.append(duration)
        self.now += duration


class FakeResponse:
    """Represent a controlled HTTP response.

    Attributes:
        status_code (int): Provider HTTP status.
        headers (Dict[str, str]): Provider response headers.
        payload (Dict[str, Any]): Returned JSON payload.
    """

    def __init__(self, status_code: int, payload: Dict[str, Any],
            headers: Dict[str, str] | None = None) -> None:
        """Initialize a controlled provider response.

        Args:
            status_code (int): HTTP response status.
            payload (Dict[str, Any]): JSON response.
            headers (Dict[str, str] | None): Optional headers.

        Returns:
            None: Initializes the response.
        """
        self.status_code = status_code
        self.payload = payload
        self.headers = headers if headers is not None else {}

    def raise_for_status(self) -> None:
        """Raise a Requests HTTP error for non-success responses.

        Raises:
            requests.HTTPError: If the status indicates a failed request.
        """
        if self.status_code >= 400:
            raise requests.HTTPError(f'HTTP {self.status_code}', response=self)

    def json(self) -> Dict[str, Any]:
        """Return the controlled JSON response.

        Returns:
            Dict[str, Any]: Response body.
        """
        return self.payload


def load_production_class(name: str, request_post: Mock,
        clock: FakeClock) -> type:
    """Load a production provider class with controlled dependencies.

    Purpose:
        Execute the complete class body without importing unrelated GIS packages.

    Args:
        name (str): Provider class to extract from sources.py.
        request_post (Mock): Controlled HTTP POST.
        clock (FakeClock): Simulated monotonic clock.

    Returns:
        type: The compiled production provider class.
    """
    tree = ast.parse((ROOT / 'sources.py').read_text(encoding='utf-8'))
    cls = next(node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == name)
    namespace: Dict[str, Any] = {
        'Any': Any,
        'Dict': Dict,
        'List': List,
        'Response': FakeResponse,
        'cfg': SimpleNamespace(OPENSKY_CLIENT_ID='client-id',
            OPENSKY_API_CLIENT_SECRET='private-client-secret'),
        'Error': WrappedProviderError,
        'Logger': lambda: SimpleNamespace(write=lambda exception: None),
        'time': clock,
        'dt': dt,
        'parsedate_to_datetime': parsedate_to_datetime,
        'requests': SimpleNamespace(
            post=request_post,
            RequestException=requests.RequestException,
            HTTPError=requests.HTTPError,
        ),
        'throw_if': validate_required,
    }
    module = ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[]))
    exec(compile(module, str(ROOT / 'sources.py'), 'exec'), namespace)
    return namespace[name]


def validate_required(name: str, value: object) -> None:
    """Reject missing mandatory provider inputs.

    Args:
        name (str): Input name.
        value (object): Candidate input value.

    Raises:
        ValueError: When a required value is missing.
    """
    if value is None or value == '':
        raise ValueError(f'Missing {name}')


class LiveWorldFailureRegressionTests(unittest.TestCase):
    """Test provider failure classification and retry behavior.

    Attributes:
        clock (FakeClock): Simulated monotonic clock for each test.
    """

    def setUp(self) -> None:
        """Reset the simulated clock for each test."""
        self.clock = FakeClock()

    def test_opensky_unauthorized_preserves_http_status_and_hides_secrets(self) -> None:
        """Classify rejected OAuth credentials without revealing their values."""
        request_post = Mock(return_value=FakeResponse(401, {'error': 'invalid_client'}))
        provider = load_production_class('OpenSkyLive', request_post, self.clock)()
        with self.assertRaises(WrappedProviderError) as context:
            provider.get_access_token()
        self.assertIsInstance(context.exception.error, requests.HTTPError)
        self.assertEqual(401, context.exception.error.response.status_code)
        self.assertIn('API client ID and client secret', str(context.exception))
        self.assertNotIn('private-client-secret', str(context.exception))
        self.assertEqual('private-client-secret',
            request_post.call_args.kwargs['data']['client_secret'])

    def test_opensky_partial_credentials_fail_before_network(self) -> None:
        """Reject incomplete credential pairs without contacting OAuth."""
        request_post = Mock()
        provider = load_production_class('OpenSkyLive', request_post, self.clock)()
        provider.client_secret = ''
        with self.assertRaises(WrappedProviderError) as context:
            provider.get_access_token()
        self.assertIsInstance(context.exception.error, ValueError)
        request_post.assert_not_called()

    def test_overpass_retry_after_then_success(self) -> None:
        """Honor server retry delay without duplicate sleeps."""
        request_post = Mock(side_effect=[
            FakeResponse(429, {}, {'Retry-After': '2'}),
            FakeResponse(200, {'elements': []}),
        ])
        provider = load_production_class('OverpassClient', request_post,
            self.clock)(timeout=10, retries=2)
        self.assertEqual({'elements': []}, provider.execute('[out:json];node(1);out;'))
        self.assertEqual([2.0], self.clock.sleeps)
        self.assertEqual(2, request_post.call_count)

    def test_overpass_http_date_retry_after_is_honored(self) -> None:
        """Honor an HTTP-date Retry-After without multiplying backoff delays."""
        retry_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=5)
        request_post = Mock(side_effect=[
            FakeResponse(503, {}, {'Retry-After': format_datetime(retry_at)}),
            FakeResponse(200, {'elements': []}),
        ])
        provider = load_production_class('OverpassClient', request_post,
            self.clock)(timeout=10, retries=2)
        self.assertEqual({'elements': []}, provider.execute('[out:json];node(1);out;'))
        self.assertEqual(1, len(self.clock.sleeps))
        self.assertGreaterEqual(self.clock.sleeps[0], 3.0)
        self.assertEqual(2, request_post.call_count)

    def test_overpass_permanent_http_failure_is_not_retried(self) -> None:
        """Stop after a permanent 400 response instead of retrying or failing over."""
        request_post = Mock(return_value=FakeResponse(400, {}))
        provider = load_production_class('OverpassClient', request_post,
            self.clock)(timeout=5, retries=2)
        with self.assertRaises(WrappedProviderError) as context:
            provider.execute('[out:json];node(1);out;')
        self.assertIn('HTTP 400', str(context.exception))
        request_post.assert_called_once()

    def test_overpass_deadline_retains_failed_endpoint_details(self) -> None:
        """Bound retries when requests consume the complete execution budget."""
        def timeout_request(url: str, data: dict, headers: dict,
                timeout: float) -> FakeResponse:
            """Simulate a blocking HTTP attempt that times out.

            Args:
                url (str): Requested endpoint.
                data (dict): Request payload.
                headers (dict): Request headers.
                timeout (float): Remaining HTTP timeout.

            Raises:
                requests.Timeout: Every simulated request times out.
            """
            self.clock.now += timeout
            raise requests.Timeout('simulated timeout')

        request_post = Mock(side_effect=timeout_request)
        provider = load_production_class('OverpassClient', request_post,
            self.clock)(timeout=2, retries=2, retry_delay=0.0)
        with self.assertRaises(WrappedProviderError) as context:
            provider.execute('[out:json];node(1);out;')
        self.assertIsInstance(context.exception.error, TimeoutError)
        self.assertIn('deadline exceeded', str(context.exception))
        self.assertIn('overpass-api.de', str(context.exception))
        self.assertLessEqual(self.clock.now, 4.0)

    def test_missing_ais_key_preserves_stale_frame_without_fetching(self) -> None:
        """Mark vessel configuration as required without invoking its fetcher."""
        source = (ROOT / 'realtime.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        func = next(node for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == 'refresh_live_world_source')
        previous = pd.DataFrame([{'EntityId': 'existing'}])
        state: Dict[str, Any] = {
            'live_world_aisstream_api_key': '',
            'live_world_df_vessels': previous,
        }
        statuses: list[dict[str, Any]] = []
        def record_source_status(source_key: str, status: str, error: str='',
                stale: bool=False, attempted_at: str='', successful_at: str='',
                error_type: str='', http_status: int=0) -> None:
            """Capture provider status without mutating unrelated session state.

            Args:
                source_key (str): Provider identifier.
                status (str): Provider state.
                error (str): Optional diagnostic.
                stale (bool): Whether retained data is from a previous refresh.
                attempted_at (str): Attempt timestamp.
                successful_at (str): Success timestamp.
                error_type (str): Underlying exception type.
                http_status (int): HTTP error status.

            Returns:
                None: Captures the provider-state update.
            """
            statuses.append({'source': source_key, 'status': status,
                'error': error, 'stale': stale, 'attempted_at': attempted_at,
                'successful_at': successful_at, 'error_type': error_type,
                'http_status': http_status})

        namespace: Dict[str, Any] = {
            'pd': pd,
            'dt': dt,
            'os': SimpleNamespace(getenv=lambda name: ''),
            'cfg': SimpleNamespace(AISSTREAM_API_KEY=''),
            'st': SimpleNamespace(session_state=state),
            'Callable': Any,
            'Error': WrappedProviderError,
            'HTTPError': requests.HTTPError,
            'LIVE_WORLD_DATA_SOURCES': {
                'vessels': {
                    'frame_key': 'live_world_df_vessels',
                },
            },
            'initialize_live_world_state': lambda: None,
            'throw_if': lambda name, value: None,
            'update_live_world_source_state': record_source_status,
        }
        module = ast.fix_missing_locations(ast.Module(body=[func], type_ignores=[]))
        exec(compile(module, str(ROOT / 'realtime.py'), 'exec'), namespace)
        fetcher = Mock(side_effect=AssertionError('Provider must not be called'))
        result = namespace['refresh_live_world_source']('vessels', fetcher)
        fetcher.assert_not_called()
        self.assertIs(result, previous)
        self.assertEqual('Configuration Required', statuses[-1]['status'])
        self.assertTrue(statuses[-1]['stale'])


if __name__ == '__main__':
    unittest.main()
