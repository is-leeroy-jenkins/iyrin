"""Regression tests for the process-local request rate limiter.

Purpose:
    Verifies rate validation, disabled throttling, and consecutive request spacing.
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from rates import RateLimiter, throw_if


class RateLimiterTests( unittest.TestCase ):
    """Verify validated limiter construction and request spacing."""

    def test_consecutive_waits_update_request_timestamp( self ) -> None:
        """Verify each interval is measured from the previous request."""
        limiter = RateLimiter( 1.0 )
        with patch( 'rates.time.time', side_effect=[ 10.0, 10.0, 10.25, 11.0, 11.1, 12.0 ] ):
            with patch( 'rates.time.sleep' ) as sleep:
                limiter.wait( )
                limiter.wait( )
                limiter.wait( )

        self.assertEqual( 3, limiter.calls )
        self.assertEqual( 2, sleep.call_count )
        self.assertAlmostEqual( 0.75, sleep.call_args_list[ 0 ].args[ 0 ] )
        self.assertAlmostEqual( 0.9, sleep.call_args_list[ 1 ].args[ 0 ] )
        self.assertAlmostEqual( 1.65, limiter.total_sleep )
        self.assertEqual( 12.0, limiter.last )

    def test_disabled_limiter_does_not_sleep( self ) -> None:
        """Verify None and nonpositive rate ceilings preserve no-throttle behavior."""
        for ceiling in (None, 0, -1):
            with self.subTest( ceiling=ceiling ):
                limiter = RateLimiter( ceiling )
                with patch( 'rates.time.sleep' ) as sleep:
                    limiter.wait( )
                sleep.assert_not_called( )
                self.assertEqual( 1, limiter.calls )

    def test_invalid_rate_is_rejected( self ) -> None:
        """Verify public rate arguments reject strings, booleans, and nonfinite values."""
        for ceiling in ('10', True, float( 'inf' ), float( 'nan' )):
            with self.subTest( ceiling=ceiling ):
                with self.assertRaises( ValueError ):
                    RateLimiter( ceiling )

    def test_empty_collection_is_rejected( self ) -> None:
        """Verify the required-argument guard rejects empty collections."""
        for value in ([], (), {}, set()):
            with self.subTest( value=value ):
                with self.assertRaises( ValueError ):
                    throw_if( 'value', value )


if __name__ == '__main__':
    unittest.main( )
