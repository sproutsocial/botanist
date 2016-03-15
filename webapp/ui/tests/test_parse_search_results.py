import os

from django.test import TestCase
from mock import patch

from ui.views import parse_search_results


FIXTURES_ROOT = os.path.join(os.path.dirname(__file__), 'fixtures')
FX = lambda *relpath: os.path.join(FIXTURES_ROOT, *relpath)

@patch('ui.views.get_repo_type')
@patch('ui.views.CODE_ROOT', '/opt/botanist/repos')
class ParseSearchResults(TestCase):
    def test_duplicate_repositories_in_github_and_bitbucket(self, get_repo_type):
        def se(filepath):
            if 'bitbucket' in filepath:
                return 'hg'
            elif 'github' in filepath:
                return 'git'
            else:
                raise Exception('thats odd')

        get_repo_type.side_effect = se
        with open(FX('duplicate_repositories_in_github_and_bitbucket.results.txt')) as f:
             output = f.read()

        results, count = parse_search_results(output, 'AbstractSendTimeJob', True)
        self.assertEqual(2, count)
        self.assertListEqual(['bitbucket', 'github'], results['sproutjobs'].keys())
        self.assertEqual('public abstract class AbstractJob implements Job {', results['sproutjobs']['bitbucket']['files']['src/main/java/com/sproutsocial/AbstractJob.java'][0]['srcline'])
        self.assertEqual('public abstract class AbstractJob implements Job {', results['sproutjobs']['github']['files']['src/main/java/com/sproutsocial/AbstractJob.java'][0]['srcline'])