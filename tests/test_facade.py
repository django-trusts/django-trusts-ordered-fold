"""Previous public-facade tests."""

from django.test import SimpleTestCase


class OrderedFoldFacadeTests(SimpleTestCase):
    def test_previous_declaration_types(self):
        self.skipTest(
            'Deferred. OrderedFold, PolarityMap, FlatToken, and '
            'register_ordered_fold are not the seam. The plugin exports '
            'OrderedFoldQueryCompiler and TrustsOrderedFoldModelBackend.'
        )
