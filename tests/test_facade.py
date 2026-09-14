"""Prove the public imports and extension-owned types."""

from inspect import getdoc

from django.test import SimpleTestCase

import trusts.core as core
import trusts_ordered_fold as package
from trusts_ordered_fold import (
    FlatToken,
    MaskEntry,
    OrderedFold,
    PermissionMaskDomain,
    PolarityMap,
    TrustsOrderedFoldModelBackend,
    register_ordered_fold,
)


class FacadeImportTest(SimpleTestCase):
    construction_names = (
        'OrderedFold',
        'PermissionMaskDomain',
        'MaskEntry',
        'PolarityMap',
        'FlatToken',
        'register_ordered_fold',
    )

    def test_construction_names_import_from_package_root(self):
        for name in self.construction_names:
            with self.subTest(name=name):
                self.assertTrue(hasattr(package, name))
                self.assertIs(getattr(package, name), globals()[name])
        self.assertIn('TrustsOrderedFoldModelBackend', package.__all__)
        self.assertIs(
            TrustsOrderedFoldModelBackend,
            package.TrustsOrderedFoldModelBackend,
        )

    def test_declaration_types_are_extension_owned(self):
        self.assertIsNot(OrderedFold, core.OrderedFold)
        self.assertIsNot(PermissionMaskDomain, core.PermissionMaskDomain)
        self.assertIsNot(MaskEntry, core.MaskEntry)
        self.assertIsNot(PolarityMap, core.PolarityMap)
        self.assertIsNot(FlatToken, core.FlatToken)
        self.assertEqual(OrderedFold.__module__, 'trusts_ordered_fold')
        self.assertEqual(register_ordered_fold.__module__, 'trusts_ordered_fold.registry')

    def test_register_ordered_fold_is_extension_owned(self):
        self.assertIs(register_ordered_fold, package.register_ordered_fold)
        self.assertIsNot(
            register_ordered_fold,
            getattr(core.BackendHandle, 'register_ordered_fold', None),
        )

    def test_import_root_is_not_trusts_ordered_fold_submodule(self):
        import trusts.ordered_fold as core_impl

        self.assertNotEqual(package.__file__, core_impl.__file__)
        self.assertNotIn('trusts_ordered_fold', core_impl.__file__)

    def test_package_and_register_are_marked_provisional(self):
        package_doc = getdoc(package)
        self.assertIn('trusts_ordered_fold', package_doc)
        self.assertIn('TrustsOrderedFoldModelBackend', package_doc)
        register_doc = getdoc(register_ordered_fold)
        self.assertIn('Provisional API:', register_doc)
        self.assertIn('excluded from the normal 1.x', register_doc)
        self.assertIn('future feature release', register_doc)
        for entry in (
            OrderedFold, PermissionMaskDomain, MaskEntry, PolarityMap, FlatToken,
        ):
            with self.subTest(entry=entry.__qualname__):
                doc = getdoc(entry)
                self.assertIn('Provisional API:', doc)
                self.assertIn('excluded from the normal 1.x', doc)
                self.assertIn('future feature release', doc)

    def test_internal_helpers_are_not_reexported_from_package_root_as_core(self):
        for name in (
            'OrderedFoldAllowed',
            'RegisteredStrategy',
            'ordered_fold_connection_supported',
        ):
            with self.subTest(name=name):
                self.assertFalse(hasattr(package, name))
                self.assertFalse(hasattr(core, name))
