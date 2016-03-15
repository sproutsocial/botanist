import os

from django.test import TestCase
from mock import patch

from ui.views import deep_link
from ui.views import get_repo_and_filepath

# git: https://bitbucket.org/sproutsocial/sprout-cassandra-storage-commons/src/master/src/main/java/com/sproutsocial/platform/storage/cassandra/config/CassContextBuilder.java?at=master&fileviewer=file-view-default#CassContextBuilder.java-30
# hg : https://bitbucket.org/sproutsocial/facebook-polling/src/default/src/main/java/com/sproutsocial/facebook/cassandra/ColumnFamilies.java?at=default&fileviewer=file-view-default#ColumnFamilies.java-8

# git: https://bitbucket.org/ sproutsocial/sprout-cassandra-storage-commons src/master  /src/main/java/com/sproutsocial/platform/storage/cassandra/config/CassContextBuilder.java ? at=master  & fileviewer=file-view-default # CassContextBuilder.java - 30
# hg : https://bitbucket.org/ sproutsocial/facebook-polling                 src/default /src/main/java/com/sproutsocial/facebook/cassandra/ColumnFamilies.java                    ? at=default & fileviewer=file-view-default # ColumnFamilies.java     - 8

FIXTURES_ROOT = os.path.join(os.path.dirname(__file__), 'fixtures')
FX = lambda *relpath: os.path.join(FIXTURES_ROOT, *relpath)

CODE_ROOT = FX('CODE_ROOT')

@patch('ui.views.ORG_NAMES', spec_set=dict)
@patch('ui.views.CODE_ROOT', CODE_ROOT)
class GetRepoAndFilePath(TestCase):
    BB_GIT_REPO_PATH = FX(CODE_ROOT, 'bitbucket/git-repo-name')
    BB_HG_REPO_PATH = FX(CODE_ROOT, 'bitbucket/hg-repo-name')
    GH_GIT_REPO_PATH = FX(CODE_ROOT, 'github/repositoryname')

    def setUp(self):
        os.system('mkdir -p %(d)s && cd %(d)s && git init' % {'d': self.BB_GIT_REPO_PATH})
        os.system('mkdir -p %(d)s && cd %(d)s && hg init' % {'d': self.BB_HG_REPO_PATH})
        os.system('mkdir -p %(d)s && cd %(d)s && git init' % {'d': self.GH_GIT_REPO_PATH})

    def tearDown(self):
        os.system('rm -rf %s' % FX(CODE_ROOT, 'github'))
        os.system('rm -rf %s' % FX(CODE_ROOT, 'bitbucket'))

    def test_deep_link_bitbucket_git(self, ORG_NAMES):
        self._setupmock(ORG_NAMES)
        ORG_NAMES['bitbucket'] = 'bborgname'
        filename = os.path.join(CODE_ROOT, 'bitbucket', 'git-repo-name', 'somedir', 'sourcefile.py')
        dl = deep_link(*get_repo_and_filepath(filename))

        self.assertEqual('https://bitbucket.org/bborgname/git-repo-name/src/master/somedir/sourcefile.py', dl)

    def test_deep_link_bitbucket_hg(self, ORG_NAMES):
        self._setupmock(ORG_NAMES)
        ORG_NAMES['bitbucket'] = 'bborgname'
        filename = os.path.join(CODE_ROOT, 'bitbucket', 'hg-repo-name', 'somedir', 'sourcefile.py')
        dl = deep_link(*get_repo_and_filepath(filename))

        self.assertEqual('https://bitbucket.org/bborgname/hg-repo-name/src/default/somedir/sourcefile.py', dl)

    def test_deep_link_bitbucket_git_with_lineno(self, ORG_NAMES):
        self._setupmock(ORG_NAMES)
        ORG_NAMES['bitbucket'] = 'bborgname'
        filename = os.path.join(CODE_ROOT, 'bitbucket', 'git-repo-name', 'somedir', 'sourcefile.py')
        dl = deep_link(*get_repo_and_filepath(filename), lineno=42)

        self.assertEqual('https://bitbucket.org/bborgname/git-repo-name/src/master/somedir/sourcefile.py#sourcefile.py-42', dl)

    def test_deep_link_bitbucket_hg_with_lineno(self, ORG_NAMES):
        self._setupmock(ORG_NAMES)
        ORG_NAMES['bitbucket'] = 'bborgname'
        filename = os.path.join(CODE_ROOT, 'bitbucket', 'hg-repo-name', 'somedir', 'sourcefile.py')
        dl = deep_link(*get_repo_and_filepath(filename), lineno=42)

        self.assertEqual('https://bitbucket.org/bborgname/hg-repo-name/src/default/somedir/sourcefile.py#sourcefile.py-42', dl)

    def test_deep_link_github(self, ORG_NAMES):
        self._setupmock(ORG_NAMES)
        ORG_NAMES['github'] = 'ghorgname'
        filename = os.path.join(CODE_ROOT, 'github', 'repositoryname', 'somedir', 'sourcefile.py')
        dl = deep_link(*get_repo_and_filepath(filename))

        self.assertEqual('https://github.com/ghorgname/repositoryname/blob/master/somedir/sourcefile.py', dl)

    def test_deep_link_github_with_lineno(self, ORG_NAMES):
        self._setupmock(ORG_NAMES)
        ORG_NAMES['github'] = 'ghorgname'
        filename = os.path.join(CODE_ROOT, 'github', 'repositoryname', 'somedir', 'sourcefile.py')
        dl = deep_link(*get_repo_and_filepath(filename), lineno=42)

        self.assertEqual('https://github.com/ghorgname/repositoryname/blob/master/somedir/sourcefile.py#L42', dl)

    def _setupmock(self, m):
        d = {}
        def getitem(key):
            return d[key]
        def setitem(key, val):
            d[key] = val
        m.__getitem__.side_effect = getitem
        m.__setitem__.side_effect = setitem


