from django.test import TestCase

from ui.views import get_query_re
from ui.views import prepare_source_line


class PrepareSourceLine(TestCase):
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