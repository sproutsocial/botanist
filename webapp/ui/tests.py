import json
import os
from django.test import TestCase
from mock import patch
from codesearch.settings import CODE_ROOT
from ui.views import deep_link
from ui.views import parse_search_results
from ui.views import get_query_re
from ui.views import get_repo_and_filepath
from ui.views import prepare_source_line


FIXTURES_ROOT = os.path.join(os.path.dirname(__file__), 'fixtures')
FX = lambda *relpath: os.path.join(FIXTURES_ROOT, *relpath)


class PrepareSearchLine(TestCase):
    def test_html_in_source_line_is_escaped_but_span_for_highlight_is_not(self):
        query = r'TODO'
        source_line = r'    <!-- TODO: need to clean up these colors below-->'
        expected = r'    &lt;!-- <span class="highlighted-search-query">TODO</span>: need to clean up these colors below--&gt;'

        query_re = get_query_re(query)
        result = prepare_source_line(query_re, source_line)
        self.assertEquals(expected, result)

    def test_regex_query_match_is_highlighted_but_as_original_matched_text(self):
        query = r'v1\/'
        source_line = r'			URLLocation="https://example.com/v1/"'
        expected = u'\t\t\tURLLocation=&quot;https://example.com/<span class="highlighted-search-query">v1/</span>&quot;'

        query_re = get_query_re(query)
        result = prepare_source_line(query_re, source_line)
        self.assertEquals(expected, result)

    def test_regex_query_match_is_highlighted_case_insensitive(self):
        query = r'todo'
        test_cases = (
            (r'    #TODO change this', u'    #<span class="highlighted-search-query">TODO</span> change this'),
            (r'        // todo do something cool', u'        // <span class="highlighted-search-query">todo</span> do something cool')
        )

        query_re = get_query_re(query, case_sensitive=False)
        for source_line, expected in test_cases:
            result = prepare_source_line(query_re, source_line)
            self.assertEquals(expected, result)

    def test_prep_search_line_with_html_disabled(self):
        query = r'todo'
        test_cases = (
            (r'    #TODO change this', u'    #TODO change this'),
            (r'        // todo do something cool', u'        // todo do something cool')
        )

        query_re = get_query_re(query, case_sensitive=False)
        for source_line, expected in test_cases:
            result = prepare_source_line(query_re, source_line, html=False)
            self.assertEquals(expected, result)


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


@patch('ui.views.CODE_ROOT', '/opt/botanist/repos')
class ParseSearchResults(TestCase):
    def test_duplicate_repositories_in_github_and_bitbucket(self):
        with open(FX('duplicate_repositories_in_github_and_bitbucket.results.txt')) as f:
             output = f.read()

        results, count = parse_search_results(output, 'AbstractSendTimeJob', True)
        self.assertEqual(2, count)
        self.assertListEqual(['bitbucket', 'github'], results['sproutjobs'].keys())
        self.assertEqual('public abstract class AbstractJob implements Job {', results['sproutjobs']['bitbucket']['files']['src/main/java/com/sproutsocial/AbstractJob.java'][0]['srcline'])
        self.assertEqual('public abstract class AbstractJob implements Job {', results['sproutjobs']['github']['files']['src/main/java/com/sproutsocial/AbstractJob.java'][0]['srcline'])
