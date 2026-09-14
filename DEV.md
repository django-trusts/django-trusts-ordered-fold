# DEV.md — internal / transitional record

This file is an internal development record. It may describe
unsupported or superseded states. The user-facing package introduction
is [README.md](README.md). `pyproject.toml` long-description metadata
points at `README.md`, not this file.

## Current pairing

This tree is `django-trusts-ordered-fold==1.0.0.dev0` pairing against
Core `dev` at `a8bacc7012b3d8d62d4b3245a9c63e44cbe733d0` (still contains
`BackendHandle.register_ordered_fold`).

P1 is the standalone façade only. Import root is `trusts_ordered_fold`.
Do not create or reuse `trusts.ordered_fold`. Do not move the engine,
open a Core or Windows PR, or add `TrustsOrderedFoldModelBackend`.

`Requires-Dist`: `django-trusts>=1.0.0.dev3,<2`.

## Verification

Pair CI pins Core `a8bacc7012b3d8d62d4b3245a9c63e44cbe733d0` only.
Package tests must prove the six public imports, the extension-owned
`register_ordered_fold(backend, source, fold)` forwarder, registration
acceptance/rejection, zero-SQL registration, exact-path ownership, and
freeze. The pinned Core kernel suite must stay green.

## License

BSD-2-Clause. Copyright holder is exactly BeeDesk, Inc. Notice years
are 2015-2026.
