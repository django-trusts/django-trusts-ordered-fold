"""Host app for ordered-fold object checks."""

from trusts.apps import TrustsConfigMixin


class FoldHostConfig(TrustsConfigMixin):
    name = 'tests.fold_host'
    label = 'fold_host'
    default = True
