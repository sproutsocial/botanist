import os

from django.test import TestCase
from mock import patch

from ui.views import deep_link
from ui.views import get_repo_and_filepath

FIXTURES_ROOT = os.path.join(os.path.dirname(__file__), 'fixtures')
FX = lambda *relpath: os.path.join(FIXTURES_ROOT, *relpath)

CODE_ROOT = FX('CODE_ROOT')

class TestMixin(object):
    GH_GIT_REPO_PATH = FX(CODE_ROOT, 'github/org-name/repositoryname')

    def setUp(self):
        os.system('mkdir -p %(d)s && cd %(d)s && git init' % {'d': self.GH_GIT_REPO_PATH})

    def tearDown(self):
        os.system('rm -rf %s' % FX(CODE_ROOT, 'github'))


@patch('ui.views.CODE_ROOT', CODE_ROOT)
class DeepLink(TestMixin, TestCase):
    GH_GIT_REPO_PATH = FX(CODE_ROOT, 'github/org-name/repositoryname')

    def setUp(self):
        os.system('mkdir -p %(d)s && cd %(d)s && git init' % {'d': self.GH_GIT_REPO_PATH})

    def tearDown(self):
        os.system('rm -rf %s' % FX(CODE_ROOT, 'github'))

    def test_deep_link_github(self):
        filename = os.path.join(CODE_ROOT, 'github', 'org-name', 'repositoryname', 'somedir', 'sourcefile.py')
        dl = deep_link(*get_repo_and_filepath(filename))

        self.assertEqual('https://github.com/org-name/repositoryname/blob/main/somedir/sourcefile.py', dl)

    def test_deep_link_github_with_lineno(self):
        filename = os.path.join(CODE_ROOT, 'github', 'org-name', 'repositoryname', 'somedir', 'sourcefile.py')
        dl = deep_link(*get_repo_and_filepath(filename), lineno=42)

        self.assertEqual('https://github.com/org-name/repositoryname/blob/main/somedir/sourcefile.py#L42', dl)

    def test_deep_link_github_with_main_branch(self):
        filename = os.path.join(CODE_ROOT, 'github', 'org-name', 'repositoryname', 'somedir', 'sourcefile.py')
        dl = deep_link(*get_repo_and_filepath(filename), lineno=42, git_branch='main')
        self.assertEqual('https://github.com/org-name/repositoryname/blob/main/somedir/sourcefile.py#L42', dl)
