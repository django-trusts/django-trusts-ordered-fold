# migrates.md — django-trusts-ordered-fold 1.0.0.dev0

This file is the **P1 façade route**. The engine still lives in Core
at `a8bacc7012b3d8d62d4b3245a9c63e44cbe733d0`. P2 will own the engine
and add `TrustsOrderedFoldModelBackend`.

Do **not** add `'trusts'` or `'trusts_ordered_fold'` to
`INSTALLED_APPS`. Core is a Python library. This package ships no
Django app in P1.

## Audience

- **Applications that already construct OrderedFold on Core:** retarget
  the six public names to `trusts_ordered_fold` now. Registration still
  lands on the current Core handle.
- **Windows ACL and later A-train slices:** complete this import
  cutover first. Do not wait for P2 to change the import root.

## P1 import and registration

| Surface | Old (Core provisional) | New (`django-trusts-ordered-fold==1.0.0.dev0`) |
| --- | --- | --- |
| Package | `django-trusts` only | `django-trusts` + `django-trusts-ordered-fold` |
| Import root | `trusts.core` / `trusts.ordered_fold` | **`trusts_ordered_fold`** |
| Declarations | `from trusts.core import OrderedFold, PermissionMaskDomain, MaskEntry, PolarityMap, FlatToken` | `from trusts_ordered_fold import OrderedFold, PermissionMaskDomain, MaskEntry, PolarityMap, FlatToken` |
| Registration | `backend.register_ordered_fold(source, fold)` | `register_ordered_fold(backend, source, fold)` |
| Handle method | public Core method | still present on Core; the package function forwards to it |
| `TrustsOrderedFoldModelBackend` | n/a | **P2.** Do not implement or list it in P1. |
| `trusts.E006` | Core vendor check | stays Core-owned until P2 (`trusts_ordered_fold.E001`) |
| Engine / PostgreSQL renderer | `trusts.ordered_fold` | stays in Core until P2 |

```python
# Old (Core provisional)
from trusts.core import (
    FlatToken,
    MaskEntry,
    OrderedFold,
    PermissionMaskDomain,
    PolarityMap,
)
backend.register_ordered_fold(Ace, OrderedFold(...))

# New (P1 façade)
from trusts_ordered_fold import (
    FlatToken,
    MaskEntry,
    OrderedFold,
    PermissionMaskDomain,
    PolarityMap,
    register_ordered_fold,
)
register_ordered_fold(backend, Ace, OrderedFold(...))
```

The five declaration types are the same objects Core exports today.
`register_ordered_fold` forwards to
`backend.register_ordered_fold(source, fold)` and therefore preserves
registration-time validation, zero-SQL registration, exact-path
ownership, and freeze behavior.

Do **not** import `trusts.ordered_fold` from this package. That module
path stays Core-owned until C2. Do not reclaim it during coexistence.

## Behavior retained in P1

| Situation | Result |
| --- | --- |
| Valid public fold on an unfrozen handle | Registers; 0 SQL; compiled strategy stored on that handle's registry only |
| `Ref` source or `Ref` fold fields | `TypeError`; store unchanged |
| Derived `source=` on the public `OrderedFold` | `TrustsConfigurationError`; store unchanged |
| Not an `OrderedFold` | `TrustsConfigurationError`; store unchanged |
| Frozen / finalized registry | `TrustsConfigurationError` **before** path parsing / validation |
| Second exact backend path | Independent registry; no leak |
| Core kernel suite at the P1 pin | Unchanged (this package does not edit Core) |

## Forward-looking A-train (not shipped in P1)

Topology A for 1.0 uses independent Django backends. These rows are the
migration map for later slices; do not treat them as available in P1.

| Surface | After P2 / C1 / W / C2 |
| --- | --- |
| Concrete backend | `TrustsOrderedFoldModelBackend` listed in `AUTHENTICATION_BACKENDS` (Windows subclasses it; one path) |
| Object `User.has_perm` | Django ordered backend OR across families |
| QuerySet / common-permission / `.authorized` | Family-local; **not** mixed-family one-SQL |
| Fold deny vs relationship grant | No same-plan veto; object OR only |
| Vendor check | `trusts_ordered_fold.E001` retires Core `trusts.E006` |
| `#187` same-path XOR / family-local OR | Provisional deferral; replaced by topology A |

## Migration-bot checklist

Search application code, Windows, GH, Zero, and docs for Core fold
imports and the new package root:

```text
from trusts.core import OrderedFold
from trusts.core import PermissionMaskDomain
from trusts.core import MaskEntry
from trusts.core import PolarityMap
from trusts.core import FlatToken
from trusts.ordered_fold import
import trusts.ordered_fold
backend.register_ordered_fold(
handle.register_ordered_fold(
.registry.register_strategy(
register_strategy(
OrderedFold(
trusts.ordered_fold
trusts.E006
SILENCED_SYSTEM_CHECKS.*E006
AnyPath and OrderedFold cannot share one terminal
already has an OrderedFold strategy
from trusts_ordered_fold import
register_ordered_fold(
TrustsOrderedFoldModelBackend
trusts_ordered_fold.E001
```

Then:

- [ ] Install `django-trusts-ordered-fold` (it requires `django-trusts>=1.0.0.dev3,<2`).
- [ ] Replace `from trusts.core import OrderedFold, PermissionMaskDomain, MaskEntry, PolarityMap, FlatToken` with `from trusts_ordered_fold import …`.
- [ ] Replace `backend.register_ordered_fold(source, fold)` call sites with `register_ordered_fold(backend, source, fold)`.
- [ ] Do not import `trusts.ordered_fold` from this package. Leave that module to Core until C2.
- [ ] Confirm the five façade types are the same objects as Core (`is` identity) so registration-time `isinstance` checks still pass.
- [ ] Confirm registration acceptance, rejection, freeze, exact-path isolation, and 0 SQL against Core `a8bacc7012b3d8d62d4b3245a9c63e44cbe733d0`.
- [ ] Do not add `'trusts'` or `'trusts_ordered_fold'` to `INSTALLED_APPS` in P1.
- [ ] Do not list `TrustsOrderedFoldModelBackend` yet (P2).
- [ ] Do not copy or move the PostgreSQL renderer.
- [ ] Do not add a Core dependency on this package.
- [ ] Do not open a Core or Windows PR in this slice.
- [ ] Detect remaining Core fold imports (`trusts.core` fold names, `trusts.ordered_fold`, `.register_strategy(`).
- [ ] Detect single-backend mixed relationship+fold registration that assumed `#187` same-plan OR; later slices require an OrderedFold backend path.
- [ ] Drop XOR / `#187` workarounds that assumed one plan once P2+C1 land.
- [ ] Windows `compat` floor still accepts Core `register_ordered_fold` until W.
- [ ] Silenced `trusts.E006` becomes `trusts_ordered_fold.E001` in P2/W; silencing still does not create a fallback grant.
- [ ] Confirm `pip` refuses core below `1.0.0.dev3` against this wheel.
- [ ] Leave package version at `1.0.0.dev0` and core floor at `1.0.0.dev3`.
