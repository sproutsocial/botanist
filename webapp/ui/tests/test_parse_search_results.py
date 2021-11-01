import json
import os

from django.test import TestCase
from mock import patch

from ui.views import parse_search_results


FIXTURES_ROOT = os.path.join(os.path.dirname(__file__), 'fixtures')
FX = lambda *relpath: os.path.join(FIXTURES_ROOT, *relpath)


@patch('ui.views.get_repo_type')
@patch('ui.views.CODE_ROOT', '/botanist/repos')
class ParseSearchResults(TestCase):
    def test_basic_parse_search_results(self, get_repo_type):
        with open(FX('basic_parse_search_results.txt')) as f:
            output = f.read()

        results, count = parse_search_results(output, 'facebook_comment', True)

        self.assertEqual(4, count)
        self.assertEqual(2, len(results['org1/repo1']['github']['files']))
        self.assertEqual('https://github.com/org1/repo1/blob/main/src/main/java/com/sproutsocial/SomeClass.java#L148',
                         results['org1/repo1']['github']['files']['src/main/java/com/sproutsocial/SomeClass.java'][0]['deeplink'])
        self.assertEqual(1, len(results['org2/repo1']['github']['files']))
        self.assertEqual(1, len(results['org2/repo2']['github']['files']))
