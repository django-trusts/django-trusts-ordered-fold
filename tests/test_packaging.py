"""Previous packaging proofs against the rc1 pin and engine module."""

from django.test import SimpleTestCase


class OrderedFoldPackagingTests(SimpleTestCase):
    def test_previous_engine_pin(self):
        self.skipTest(
            'Deferred. The package no longer ships engine.py or the '
            'rc1 companion pin. Metadata is checked by the wheel job; '
            'this file used to assert the deleted renderer.'
        )
