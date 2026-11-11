"""Previous remaining-bits registry tests.

Skipped: this round folds permission-matched rows from register().
It does not reimplement the mask domain, token bag, or descriptor walk.
"""

from django.test import SimpleTestCase


_REASON = (
    'Registration, mask-domain, and renderer tests are not the object '
    'check. Single-object has_perm for direct ACEs and a one-level flat '
    'token is tests.test_has_perm. Descriptor equality and the multi-hop '
    'to_field collision graph are not a register() content path, so those '
    'has_perm scenarios are not ported.'
)


class OrderedFoldRegistrationTest(SimpleTestCase):
    def test_previous_registry_surface(self):
        self.skipTest(_REASON)


class OrderedFoldAuthorizationTest(SimpleTestCase):
    def test_previous_runtime_matrix(self):
        self.skipTest(_REASON)


class OrderedFoldFlatTokenTest(SimpleTestCase):
    def test_previous_flat_token(self):
        self.skipTest(_REASON)
