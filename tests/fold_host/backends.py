"""Backend the has_perm tests list in AUTHENTICATION_BACKENDS."""

from trusts_ordered_fold.backends import TrustsOrderedFoldModelBackend
from trusts_ordered_fold.compiler import OrderedFoldQueryCompiler


class FoldHostBackend(TrustsOrderedFoldModelBackend):
    query_compiler = OrderedFoldQueryCompiler(
        order='ace_order',
        polarity='ace_type',
        allow=1,
        deny=2,
        mask='access_mask',
        trustee='user',
        masks=(('read', 0x1), ('write', 0x2), ('readwrite', 0x3)),
    )
