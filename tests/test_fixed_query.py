"""Previous fixed-query and named-filter projection tests."""

from django.test import SimpleTestCase


class OrderedFoldFixedQueryTests(SimpleTestCase):
    def test_previous_queryset_projections(self):
        self.skipTest(
            'Deferred. This round does not answer filter_authorized, '
            'named filters on a queryset, or the one-SQL list inquiry. '
            'A queryset has_perm stays fail-closed.'
        )
