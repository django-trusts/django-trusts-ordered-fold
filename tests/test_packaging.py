"""Source-tree proofs that P1 is a façade, not an engine move."""

from pathlib import Path

from django.test import SimpleTestCase


ROOT = Path(__file__).resolve().parents[1]
COMPANION = 'a8bacc7012b3d8d62d4b3245a9c63e44cbe733d0'


class OrderedFoldSourceLayoutTests(SimpleTestCase):
    def test_import_root_is_trusts_ordered_fold(self):
        self.assertTrue((ROOT / 'trusts_ordered_fold' / '__init__.py').is_file())
        self.assertFalse((ROOT / 'trusts').exists())
        self.assertFalse((ROOT / 'trusts_ordered_fold' / 'ordered_fold.py').exists())

    def test_package_does_not_copy_postgresql_renderer(self):
        offenders = []
        banned = (
            'WITH RECURSIVE',
            'render_ordered_fold_sql',
            'class OrderedFoldAllowed',
            'class RegisteredStrategy',
            'def validate_ordered_fold',
        )
        for path in (ROOT / 'trusts_ordered_fold').rglob('*.py'):
            text = path.read_text()
            for needle in banned:
                if needle in text:
                    offenders.append('%s: %s' % (path.relative_to(ROOT), needle))
        self.assertEqual(offenders, [])

    def test_no_test_modules_under_installable_package(self):
        package_dir = ROOT / 'trusts_ordered_fold'
        offenders = [
            path.relative_to(ROOT).as_posix()
            for path in package_dir.rglob('*.py')
            if path.name == 'tests.py' or path.name.startswith('test_')
            or path.parent.name in {'tests', 'test'}
        ]
        self.assertEqual(offenders, [])


class OrderedFoldPublishMetadataTests(SimpleTestCase):
    def test_pyproject_requires_core_floor_and_pin(self):
        text = (ROOT / 'pyproject.toml').read_text()
        self.assertIn('name = "django-trusts-ordered-fold"', text)
        self.assertIn('version = "1.0.0.dev0"', text)
        self.assertIn('"django-trusts>=1.0.0.dev3,<2"', text)
        self.assertIn('"Django>=6.1,<6.2"', text)
        self.assertIn('readme = "README.md"', text)
        self.assertNotIn('readme = "DEV.md"', text)
        self.assertIn('license = "BSD-2-Clause"', text)
        self.assertIn('"trusts_ordered_fold"', text)
        self.assertNotIn('"trusts.ordered_fold"', text)
        req = (ROOT / 'requirements.txt').read_text()
        ci = (ROOT / '.github' / 'workflows' / 'ci.yml').read_text()
        dev = (ROOT / 'DEV.md').read_text()
        self.assertIn(COMPANION, req)
        self.assertIn('COMPANION_KERNEL_SHA: %s' % COMPANION, ci)
        self.assertIn(COMPANION, dev)

    def test_license_notice_is_beedesk_2015_2026(self):
        text = (ROOT / 'LICENSE').read_text()
        self.assertIn('Copyright (c) 2015-2026, BeeDesk, Inc.', text)
        self.assertNotIn('and contributors', text.split('THIS SOFTWARE')[0])
        self.assertIn('BSD-2-Clause', (ROOT / 'pyproject.toml').read_text())

    def test_user_readme_is_not_internal_status(self):
        readme = (ROOT / 'README.md').read_text()
        forbidden = (
            'baton',
            'code budget',
            'kernel_config',
            'IIa',
            '2.0.0.dev',
        )
        offenders = [needle for needle in forbidden if needle in readme]
        self.assertEqual(offenders, [])
        self.assertIn('pip install django-trusts-ordered-fold', readme)
        self.assertIn('from trusts_ordered_fold import', readme)
        self.assertIn('register_ordered_fold', readme)
        self.assertIn('provisional', readme.lower())
        self.assertIn('TrustsOrderedFoldModelBackend', readme)
        self.assertIn('migrates.md', readme)
        self.assertIn(COMPANION, readme)
        dev = (ROOT / 'DEV.md').read_text()
        self.assertIn('internal', dev[:800].lower())
        self.assertIn('transitional', dev[:800].lower())

    def test_migrates_lists_old_and_new_imports(self):
        text = (ROOT / 'migrates.md').read_text()
        self.assertIn('from trusts.core import OrderedFold', text)
        self.assertIn('from trusts_ordered_fold import', text)
        self.assertIn('register_ordered_fold(backend, source, fold)', text)
        self.assertIn('backend.register_ordered_fold', text)
        self.assertIn('trusts.ordered_fold', text)
        self.assertIn('TrustsOrderedFoldModelBackend', text)
        self.assertIn('trusts_ordered_fold.E001', text)
        self.assertIn('Migration-bot checklist', text)
