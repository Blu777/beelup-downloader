"""
Tests for the rate limiter in app.py.

Demonstrates a TOCTOU (Time-of-Check-Time-of-Use) race condition
in _consume_rate_limit and verifies the fix.
"""

import threading
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import (
    app,
    _RATE_LIMIT_BUCKETS,
    _consume_rate_limit,
    _is_rate_limited,
    _record_rate_limit_hit,
    _reset_rate_limit,
    _prune_rate_limit_hits,
)


class TestRateLimiterTOCTOU:
    """
    Proves the TOCTOU vulnerability: _is_rate_limited and
    _record_rate_limit_hit use separate lock acquisitions.
    Between the two calls another thread can slip through.
    """

    def test_sequential_interleaving_proves_bug(self):
        """
        Simulates the exact interleaving that causes the race:
          T-A: _is_rate_limited -> False  (4 hits, 4 < 5)
          T-B: _is_rate_limited -> False  (4 hits, 4 < 5)
          T-A: _record_rate_limit_hit     (5 hits)
          T-B: _record_rate_limit_hit     (6 hits!)

        Both threads believe they are within the limit, but the result
        is 6 recorded hits — one more than max_hits=5.
        """
        MAX_HITS = 5
        WINDOW = 60

        with app.test_request_context(environ_base={"REMOTE_ADDR": "10.0.0.1"}):
            _RATE_LIMIT_BUCKETS.clear()

            # Pre-fill 4 hits (one below the limit)
            for _ in range(MAX_HITS - 1):
                _record_rate_limit_hit("toctou_proof", WINDOW)

            # --- Interleaving begins ---
            # Thread A checks: 4 < 5 → not limited
            check_a = _is_rate_limited("toctou_proof", MAX_HITS, WINDOW)
            # Thread B checks: still 4 < 5 → not limited
            check_b = _is_rate_limited("toctou_proof", MAX_HITS, WINDOW)

            assert check_a is False, "Thread A must see 4 < 5"
            assert check_b is False, "Thread B must see 4 < 5"

            # Both threads proceed to record their hits
            _record_rate_limit_hit("toctou_proof", WINDOW)  # Thread A → 5
            _record_rate_limit_hit("toctou_proof", WINDOW)  # Thread B → 6

            key = ("toctou_proof", "10.0.0.1")
            now = time.time()
            actual_hits = len(
                _prune_rate_limit_hits(
                    _RATE_LIMIT_BUCKETS[key]["hits"], now, WINDOW
                )
            )

            assert actual_hits == MAX_HITS + 1, (
                f"Expected {MAX_HITS + 1} hits (proving the race), got {actual_hits}"
            )


class TestRateLimiterFixed:
    """
    After the fix, _consume_rate_limit is atomic: check + record
    happen inside one single lock acquisition.
    """

    def test_atomic_consume_respects_limit(self):
        """
        Calling _consume_rate_limit serially must allow exactly
        max_hits requests and reject the rest.
        """
        MAX_HITS = 5
        WINDOW = 60

        with app.test_request_context(environ_base={"REMOTE_ADDR": "10.0.0.3"}):
            _RATE_LIMIT_BUCKETS.clear()

            results = [
                _consume_rate_limit("fixed_serial", MAX_HITS, WINDOW)
                for _ in range(MAX_HITS + 5)
            ]

            allowed = sum(1 for r in results if r)
            assert allowed == MAX_HITS, (
                f"Expected exactly {MAX_HITS} allowed, got {allowed}"
            )

    def test_atomic_consume_under_concurrency(self):
        """
        Under concurrency the fixed version must still respect the
        limit exactly, because check-and-record is now atomic.
        """
        MAX_HITS = 5
        WINDOW = 60
        NUM_THREADS = 50

        with app.test_request_context(environ_base={"REMOTE_ADDR": "10.0.0.4"}):
            _RATE_LIMIT_BUCKETS.clear()

            results = []
            barrier = threading.Barrier(NUM_THREADS)

            def attempt():
                with app.test_request_context(
                    environ_base={"REMOTE_ADDR": "10.0.0.4"}
                ):
                    barrier.wait()
                    ok = _consume_rate_limit("fixed_concurrent", MAX_HITS, WINDOW)
                    results.append(ok)

            threads = [threading.Thread(target=attempt) for _ in range(NUM_THREADS)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            allowed = sum(1 for r in results if r)
            assert allowed == MAX_HITS, (
                f"Expected exactly {MAX_HITS} allowed under concurrency, "
                f"got {allowed}"
            )

    def test_window_expiry_allows_new_requests(self):
        """Hits outside the window must not count."""
        MAX_HITS = 2
        WINDOW = 1  # 1-second window

        with app.test_request_context(environ_base={"REMOTE_ADDR": "10.0.0.5"}):
            _RATE_LIMIT_BUCKETS.clear()

            assert _consume_rate_limit("expiry", MAX_HITS, WINDOW) is True
            assert _consume_rate_limit("expiry", MAX_HITS, WINDOW) is True
            assert _consume_rate_limit("expiry", MAX_HITS, WINDOW) is False

            time.sleep(1.1)

            assert _consume_rate_limit("expiry", MAX_HITS, WINDOW) is True

    def test_reset_clears_bucket(self):
        """_reset_rate_limit must allow requests again."""
        MAX_HITS = 2
        WINDOW = 60

        with app.test_request_context(environ_base={"REMOTE_ADDR": "10.0.0.6"}):
            _RATE_LIMIT_BUCKETS.clear()

            assert _consume_rate_limit("reset_test", MAX_HITS, WINDOW) is True
            assert _consume_rate_limit("reset_test", MAX_HITS, WINDOW) is True
            assert _consume_rate_limit("reset_test", MAX_HITS, WINDOW) is False

            _reset_rate_limit("reset_test")

            assert _consume_rate_limit("reset_test", MAX_HITS, WINDOW) is True

    def test_different_scopes_are_independent(self):
        """Rate limits for different scopes must not interfere."""
        MAX_HITS = 2
        WINDOW = 60

        with app.test_request_context(environ_base={"REMOTE_ADDR": "10.0.0.7"}):
            _RATE_LIMIT_BUCKETS.clear()

            assert _consume_rate_limit("scope_a", MAX_HITS, WINDOW) is True
            assert _consume_rate_limit("scope_a", MAX_HITS, WINDOW) is True
            assert _consume_rate_limit("scope_a", MAX_HITS, WINDOW) is False

            # scope_b is independent
            assert _consume_rate_limit("scope_b", MAX_HITS, WINDOW) is True
            assert _consume_rate_limit("scope_b", MAX_HITS, WINDOW) is True
            assert _consume_rate_limit("scope_b", MAX_HITS, WINDOW) is False

    def test_different_ips_are_independent(self):
        """Rate limits for different IPs must not interfere."""
        MAX_HITS = 2
        WINDOW = 60

        _RATE_LIMIT_BUCKETS.clear()

        with app.test_request_context(environ_base={"REMOTE_ADDR": "192.168.1.1"}):
            assert _consume_rate_limit("ip_test", MAX_HITS, WINDOW) is True
            assert _consume_rate_limit("ip_test", MAX_HITS, WINDOW) is True
            assert _consume_rate_limit("ip_test", MAX_HITS, WINDOW) is False

        with app.test_request_context(environ_base={"REMOTE_ADDR": "192.168.1.2"}):
            assert _consume_rate_limit("ip_test", MAX_HITS, WINDOW) is True
