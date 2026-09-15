"""Concrete OrderedFold Django backend."""

from django.contrib.auth.backends import ModelBackend

from trusts.backends import TrustModelBackendMixin
from trusts_ordered_fold.registry import OrderedFoldQueryCompiler


class TrustsOrderedFoldModelBackend(TrustModelBackendMixin, ModelBackend):
    """Independent Django auth backend for the OrderedFold family.

    List this path (or a subclass such as Windows ``WinfsBackend``) in
    ``AUTHENTICATION_BACKENDS``. Do not also list a relationship backend
    for the same content terminal as a mixed-family 1.0 contract.
    """

    query_compiler = OrderedFoldQueryCompiler()
