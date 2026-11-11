"""Previous register_ordered_fold tests."""

from django.test import SimpleTestCase


class OrderedFoldRegisterTests(SimpleTestCase):
    def test_previous_register_ordered_fold(self):
        self.skipTest(
            'Deferred. Registration is trusts register() '
            '(user, permission, content, condition, along, via). '
            'There is no parallel register_ordered_fold.'
        )
