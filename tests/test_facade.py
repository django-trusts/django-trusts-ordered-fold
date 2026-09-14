"""Prove the six public imports and Core-identity façade."""

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
    register_ordered_fold,
)


class FacadeImportTest(SimpleTestCase):
    public_names = (
        'OrderedFold',
        'PermissionMaskDomain',
        'MaskEntry',
        'PolarityMap',
        'FlatToken',
        'register_ordered_fold',
    )

    def test_six_names_import_from_package_root(self):
        self.assertEqual(
            set(package.__all__),
            set(self.public_names),
        )
        for name in self.public_names:
            with self.subTest(name=name):
                self.assertTrue(hasattr(package, name))
                self.assertIs(getattr(package, name), globals()[name])

    def test_declaration_types_are_core_identity(self):
        self.assertIs(OrderedFold, core.OrderedFold)
        self.assertIs(PermissionMaskDomain, core.PermissionMaskDomain)
        self.assertIs(MaskEntry, core.MaskEntry)
        self.assertIs(PolarityMap, core.PolarityMap)
        self.assertIs(FlatToken, core.FlatToken)

    def test_register_ordered_fold_is_extension_owned(self):
        self.assertIs(register_ordered_fold, package.register_ordered_fold)
        self.assertIsNot(register_ordered_fold, core.BackendHandle.register_ordered_fold)
        self.assertEqual(register_ordered_fold.__module__, 'trusts_ordered_fold')

    def test_import_root_is_not_trusts_ordered_fold_submodule(self):
        import trusts.ordered_fold as core_impl

        self.assertNotEqual(package.__file__, core_impl.__file__)
        self.assertNotIn('trusts_ordered_fold', core_impl.__file__)

    def test_package_and_register_are_marked_provisional(self):
        package_doc = getdoc(package)
        self.assertIn('provisional', package_doc.lower())
        self.assertIn('trusts_ordered_fold', package_doc)
        self.assertIn('TrustsOrderedFoldModelBackend', package_doc)
        register_doc = getdoc(register_ordered_fold)
        self.assertIn('Provisional API:', register_doc)
        self.assertIn('excluded from the normal 1.x', register_doc)
        self.assertIn('future feature release', register_doc)
        self.assertIn('backend.register_ordered_fold', register_doc)
