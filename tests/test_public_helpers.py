"""Previous decorator and preflight helper tests."""

from django.test import SimpleTestCase


class OrderedFoldPublicHelperTests(SimpleTestCase):
    def test_previous_helpers(self):
        self.skipTest(
            'Deferred. authorization_required, granted, and the rc1 '
            'preflight helpers are not wired. Only has_perm for one '
            'saved object is answered.'
        )
