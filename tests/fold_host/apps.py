"""Installed OrderedFold implementation owner for package tests."""

from trusts_ordered_fold.apps import OrderedFoldImplementationConfig


FOLD_BACKEND = 'trusts_ordered_fold.backends.TrustsOrderedFoldModelBackend'


class FoldHostConfig(OrderedFoldImplementationConfig):
    name = 'tests.fold_host'
    label = 'fold_host'
    default = True
    trusts_backend_paths = (FOLD_BACKEND,)
