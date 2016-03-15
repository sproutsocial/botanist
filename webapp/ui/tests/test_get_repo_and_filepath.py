import os

from django.test import TestCase
from mock import patch

from codesearch.settings import CODE_ROOT
from ui.views import deep_link
from ui.views import get_repo_and_filepath


@patch('ui.views.ORG_NAMES', spec_set=dict)
class GetRepoAndFilePath(TestCase):

    def test_deep_link_bitbucket(self, ORG_NAMES):
        self._setupmock(ORG_NAMES)
        ORG_NAMES['bitbucket'] = 'bborgname'
        filename = os.path.join(CODE_ROOT, 'bitbucket', 'repositoryname', 'somedir', 'sourcefile.py')
        vcs_loc, reponame, filename = get_repo_and_filepath(filename)
        dl = deep_link(vcs_loc, reponame, filename)

        self.assertEqual('https://bitbucket.org/bborgname/repositoryname/src/tip/somedir/sourcefile.py', dl)

    def test_deep_link_bitbucket_with_lineno(self, ORG_NAMES):
        self._setupmock(ORG_NAMES)
        ORG_NAMES['bitbucket'] = 'bborgname'
        filename = os.path.join(CODE_ROOT, 'bitbucket', 'repositoryname', 'somedir', 'sourcefile.py')
        vcs_loc, reponame, filename = get_repo_and_filepath(filename)
        dl = deep_link(vcs_loc, reponame, filename, lineno=42)

        self.assertEqual('https://bitbucket.org/bborgname/repositoryname/src/tip/somedir/sourcefile.py#sourcefile.py-42', dl)

    def test_deep_link_github(self, ORG_NAMES):
        self._setupmock(ORG_NAMES)
        ORG_NAMES['github'] = 'ghorgname'
        filename = os.path.join(CODE_ROOT, 'github', 'repositoryname', 'somedir', 'sourcefile.py')
        vcs_loc, reponame, filename = get_repo_and_filepath(filename)
        dl = deep_link(vcs_loc, reponame, filename)

        self.assertEqual('https://github.com/ghorgname/repositoryname/blob/master/somedir/sourcefile.py', dl)

    def test_deep_link_github_with_lineno(self, ORG_NAMES):
        self._setupmock(ORG_NAMES)
        ORG_NAMES['github'] = 'ghorgname'
        filename = os.path.join(CODE_ROOT, 'github', 'repositoryname', 'somedir', 'sourcefile.py')
        vcs_loc, reponame, filename = get_repo_and_filepath(filename)
        dl = deep_link(vcs_loc, reponame, filename, lineno=42)

        self.assertEqual('https://github.com/ghorgname/repositoryname/blob/master/somedir/sourcefile.py#L42', dl)

    def _setupmock(self, m):
        d = {}
        def getitem(key):
            return d[key]
        def setitem(key, val):
            d[key] = val
        m.__getitem__.side_effect = getitem
        m.__setitem__.side_effect = setitem


