"""Implementation owner for an OrderedFold backend path.

Not installed by this package. Host apps subclass this, set
``trusts_backend_paths``, and donate folds from ``ready()``.
"""

from trusts.apps import TrustsImplementationConfig
from trusts_ordered_fold.registry import (
    OrderedFoldBackendHandle,
    OrderedFoldRegistry,
)


class OrderedFoldImplementationConfig(TrustsImplementationConfig):
    """Implementation owner for an OrderedFold backend path.

    Not installed by this package. Host apps subclass this, set
    ``trusts_backend_paths``, and donate folds from ``ready()``.
    """

    # Protected / provisional. Not a public family API.
    _authorization_family = 'ordered_fold'

    def _create_registry(self, path):
        return OrderedFoldRegistry()

    def _create_handle(self, path, registry, compiler):
        return OrderedFoldBackendHandle(
            path=path, registry=registry, compiler=compiler,
        )
