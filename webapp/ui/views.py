import json
import logging
import os
import pipes
import re
import time

from collections import OrderedDict
from subprocess import Popen
from subprocess import PIPE

from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.utils.html import escape

from django.shortcuts import render

from codesearch.settings import BIN_PATH
from codesearch.settings import CODE_ROOT
from codesearch.settings import ORG_NAME


HIGHLIGHT_QUERY_TEMPLATE = r'<span class="highlighted-search-query">\1</span>'
BB_DEEP_LINK_FMT = 'https://bitbucket.org/%(orgname)s/%(repo)s/src/tip/%(fpath)s'
BB_LINENO_SUFFIX_FMT = '#cl-%s'
GH_DEEP_LINK_FMT = 'https://github.com/%(orgname)s/%(repo)s/blob/master/%(fpath)s'
GH_LINENO_SUFFIX_FMT = '#L%s'

log = logging.getLogger(__name__)

class RegexError(Exception):
    pass

def index(request):
    return render(request, 'index.html')

def search(request):
    query = request.GET.get('q')
    case_sensitive = request.GET.get('case', '').lower() != 'insensitive'
    if query is None:
        return HttpResponseBadRequest()

    s = time.time()
    output = do_search(query, case_sensitive)

    results, count, error = None, None, None
    try:
        results, count = parse_search_results(output, query, case_sensitive)
    except RegexError as e:
        error = e.message
    ts = "%.2f seconds" % (time.time() - s)
    log.info('search time=%s', ts)

    context = {'query': query, 'result_count': count, 'results': results, 'time': ts, 'error': error}
    return render(request, 'search.html', context)

def search_json(request):
    query = request.GET.get('q')
    case_sensitive = request.GET.get('case', '').lower() != 'insensitive'
    if query is None:
        return HttpResponseBadRequest()

    output = do_search(query, case_sensitive)
    results, count, error = None, None, None
    try:
        results, count = parse_search_results(output, query, case_sensitive, html=False)
    except RegexError as e:
        error = e.message

    return render_json({'results': results, 'count': count, 'error': error})


def render_json(data):
    return HttpResponse(json.dumps({'data': data}), content_type="application/json")

###### to be refactored

def do_search(query, case_sensitive=True):
    # this is extremely important security code here, this
    # prevents shell code injection
    safe_query = pipes.quote(query)

    case_arg = '' if case_sensitive else  '-i'
    executable = os.path.join(BIN_PATH, 'csearch')
    cmd = '%s -n %s %s' % (executable, case_arg, safe_query)

    p = Popen([cmd], stdout=PIPE, shell=True)
    out, err = p.communicate()
    return out


def prepare_source_line(query_re, srcline, html=True):
    if html:
        # important!!! escape src manually here to avoid our own markup we
        # might have in source code from not showing up properly in code
        # search reuslts. in the django template we mark this value as
        # safe, which disables escaping to allow us to render the searched
        # term as highlighted in the search results.
        srcline = escape(srcline)
        # highlight the text that we matched on to make it easy to see in the UI
        srcline = query_re.sub(HIGHLIGHT_QUERY_TEMPLATE, srcline)

    return srcline


def get_query_re(query, case_sensitive=True):
    try:
        if case_sensitive:
            return re.compile(r'(' + query + r')')
        else:
            return re.compile(r'(' + query + r')', flags=re.IGNORECASE)
    except Exception as e:
        raise RegexError(e)


def parse_search_results(result_text, query, case_sensitive=True, html=True):
    query_re = get_query_re(query, case_sensitive)
    lines = filter(lambda l: l != '', result_text.split('\n'))
    results, count = {}, 0
    for line in lines:
        log.debug('line=%s', line)
        fields = line.split(':', 2) # don't split on colons that are part of source code :)
        try:
            filename, lineno, srcline = fields
            # codesearch's line #s are off by one
            # https://github.com/google/codesearch/issues/25
            lineno = str(long(lineno)+1)
            vcs_loc, reponame, filename = get_repo_and_filepath(filename)
            if is_vcs_folder(filename):
                continue

            count += 1

            result = {
                'filename': filename,
                'lineno': long(lineno),
                'srcline': prepare_source_line(query_re, srcline, html),
                'deeplink': deep_link(vcs_loc, reponame, filename, lineno),
                'count': count}
            if reponame not in results:
                results[reponame] = {}
                results[reponame]['vcs_loc'] = vcs_loc
                results[reponame]['files'] = OrderedDict()
            if filename not in results[reponame]['files']:
                results[reponame]['files'][filename] = []

            results[reponame]['files'][filename].append(result)
        except ValueError as e:
            log.error('ValueError: %s (cause: %s)', fields, e)

    # sort results -- have to because the lines are sorted lexicographically
    # but within each repository source site (bitbucket, github) due to
    # CODE_ROOT directory structure layout. we want it to be sorted
    # lexicographically across all repository sources
    results = OrderedDict((k, results[k]) for k in sorted(results.keys()))
    return results, count


def is_vcs_folder(filename):
    return filename.startswith('.hg') or filename.startswith('.git')


def get_repo_and_filepath(fully_qualified_filename):
    relpath = os.path.relpath(fully_qualified_filename, CODE_ROOT)
    vcs_loc, reponame, rel_file_path = relpath.split('/', 2)
    return vcs_loc, reponame, rel_file_path


def deep_link(vcs_loc, reponame, filepath, lineno=None):
    if vcs_loc not in ('github', 'bitbucket'):
        raise ValueError('unknown vcs location: %s' % vcs_loc)

    fmt = BB_DEEP_LINK_FMT if vcs_loc == 'bitbucket' else GH_DEEP_LINK_FMT
    lineno_suffix_fmt = BB_LINENO_SUFFIX_FMT if vcs_loc == 'bitbucket' else GH_LINENO_SUFFIX_FMT

    kwargs = {'orgname': ORG_NAME, 'repo': reponame, 'fpath': filepath}
    link = fmt % kwargs
    link += lineno_suffix_fmt % lineno if lineno else ''

    return link
