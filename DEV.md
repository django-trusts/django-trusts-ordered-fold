# DEV.md — internal / transitional record

This file is an internal development record. It may describe
unsupported or superseded states. The user-facing package introduction
is [README.md](README.md). `pyproject.toml` long-description metadata
points at `README.md`, not this file.

## Current pairing

This tree is `django-trusts-ordered-fold==1.0.0.dev0` pairing against
Core `DEV_standalone_ordered_fold` at
`b2ad8aa052eef25fd05a79b2dfba7b7049af148d` (C2 tip from Core PR #197;
product deletion is `72b41a0cd1d3746ac0eb82ad220eec9b559d6f7b`).
Core no longer ships OrderedFold shims
(`BackendHandle.register_ordered_fold`, `trusts.ordered_fold`,
declaration re-exports, or `TrustsRegistry.strategies`).

P2 owns the PostgreSQL OrderedFold engine and the concrete
`TrustsOrderedFoldModelBackend`. Import root is `trusts_ordered_fold`.
Do not create or reuse `trusts.ordered_fold`. Topology A only: no
relationship registration, mixed plan, sibling borrowing,
`attach_grant_branch`, callbacks, or Core imports of this package.

`Requires-Dist`: `django-trusts>=1.0.0.dev3,<2`.

## Verification

Pair CI pins Core `b2ad8aa052eef25fd05a79b2dfba7b7049af148d` only.
Package tests must prove public imports, extension-owned
`register_ordered_fold`, registration acceptance/rejection, zero-SQL
registration, exact-path ownership, freeze, validation, renderer,
fail-closed vendor gate, fixed query count, `trusts_ordered_fold.E001`,
and `TrustsOrderedFoldModelBackend`. PostgreSQL CI runs the ported
engine suite. The pinned Core kernel suite must stay green.

## License

BSD-2-Clause. Copyright holder is exactly BeeDesk, Inc. Notice year
is 2026.
