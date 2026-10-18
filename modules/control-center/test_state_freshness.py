"""Regression cases for untrusted timestamps, without device or service access."""
import json
import unittest

from adapters import field, snapshot


class FreshnessTests(unittest.TestCase):
    def test_future_observation_cannot_claim_observed(self):
        result = field('touch_mode', True, 1, 106, 45, 'fixture', now=100)
        self.assertEqual(result['health'], 'unknown')

    def test_freshness_boundaries_match_shared_ui(self):
        for observed_at, expected in [(105, 'observed'), (100, 'observed'),
                                      (55, 'observed'), (54, 'stale')]:
            with self.subTest(observed_at=observed_at):
                self.assertEqual(field('x', True, False, observed_at, 45,
                                       'fixture', now=100)['health'], expected)

    def test_invalid_observation_is_unknown_and_serializable(self):
        for value in [None, '100', True, float('nan'), float('inf'), -float('inf'), 10**400]:
            with self.subTest(value=value):
                try:
                    result = field('x', True, False, value, 45, 'fixture', now=100)
                except (TypeError, ValueError, OverflowError) as error:
                    self.fail(f'invalid timestamp escaped adapter: {type(error).__name__}')
                self.assertEqual(result['health'], 'unknown')
                self.assertIsNone(result['observed_at'])
                json.dumps(result, allow_nan=False)

    def test_invalid_lifetime_cannot_claim_observed(self):
        for value in [None, '45', True, -1, float('nan'), float('inf')]:
            with self.subTest(value=value):
                try:
                    result = field('x', True, 1, 100, value, 'fixture', now=100)
                except (TypeError, ValueError) as error:
                    self.fail(f'invalid lifetime escaped adapter: {type(error).__name__}')
                self.assertEqual(result['health'], 'unknown')
                self.assertIsNone(result['stale_after'])
                json.dumps(result, allow_nan=False)

    def test_invalid_flight_time_preserves_recovery_without_false_success(self):
        for value in [None, '100', True, float('nan'), float('inf'), 10**400]:
            with self.subTest(value=value):
                try:
                    result = snapshot(100, {'flight_saved': True, 'flight_active': True,
                                           'flight_observed_at': value}, {}, [])
                except (TypeError, ValueError, OverflowError) as error:
                    self.fail(f'invalid flight timestamp broke snapshot: {type(error).__name__}')
                self.assertIsNone(result['flight_active'])
                self.assertTrue(result['flight_saved'])
                self.assertIsNone(result['flight_observed_at'])
                json.dumps(result, allow_nan=False)

    def test_flight_time_retains_strict_no_future_policy(self):
        for observed_at, expected in [(101, None), (100, True), (55, True), (54, None)]:
            with self.subTest(observed_at=observed_at):
                result = snapshot(100, {'flight_active': True,
                                       'flight_observed_at': observed_at}, {}, [])
                self.assertIs(result['flight_active'], expected)
