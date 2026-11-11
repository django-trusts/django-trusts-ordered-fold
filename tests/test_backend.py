"""Previous backend-family and system-check tests."""

from django.test import SimpleTestCase


class OrderedFoldBackendTests(SimpleTestCase):
    def test_previous_backend_checks(self):
        self.skipTest(
            'Deferred. The host app extends TrustsConfigMixin and lists '
            'a FoldHostBackend. trusts_ordered_fold.E001 and the rc1 '
            'family factories are not part of the has_perm seam.'
        )
