"""Source-tree proofs that P2 owns the engine and pins C1."""

from pathlib import Path

from django.test import SimpleTestCase


ROOT = Path(__file__).resolve().parents[1]
COMPANION = '6934894489d4fc0e46de88b55b9a27f5f2eb2b41'


class OrderedFoldSourceLayoutTests(SimpleTestCase):
    def test_import_root_is_trusts_ordered_fold(self):
        self.assertTrue((ROOT / 'trusts_ordered_fold' / '__init__.py').is_file())
        self.assertTrue((ROOT / 'trusts_ordered_fold' / 'engine.py').is_file())
        self.assertTrue((ROOT / 'trusts_ordered_fold' / 'backends.py').is_file())
        self.assertFalse((ROOT / 'trusts').exists())

    def test_package_owns_postgresql_renderer(self):
        engine = (ROOT / 'trusts_ordered_fold' / 'engine.py').read_text()
        self.assertIn('WITH RECURSIVE', engine)
        self.assertIn('render_ordered_fold_sql', engine)
        self.assertIn('class OrderedFoldAllowed', engine)
        self.assertIn('def validate_ordered_fold', engine)
        backend = (ROOT / 'trusts_ordered_fold' / 'backends.py').read_text()
        self.assertIn('class TrustsOrderedFoldModelBackend', backend)

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
        self.assertIn('tests-orderedfold-pg', ci)

    def test_license_notice_is_beedesk_2026(self):
        text = (ROOT / 'LICENSE').read_text()
        self.assertIn('Copyright (c) 2026, BeeDesk, Inc.', text)
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
        self.assertIn('TrustsOrderedFoldModelBackend', readme)
        self.assertIn('trusts_ordered_fold.E001', readme)
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
        self.assertIn('TrustsOrderedFoldModelBackend', text)
        self.assertIn('trusts_ordered_fold.E001', text)
        self.assertIn('Migration-bot checklist', text)
        self.assertIn(COMPANION, text)
