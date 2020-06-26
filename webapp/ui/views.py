import json
import logging
import pipes
import re
import time

from collections import OrderedDict
from subprocess import Popen
from subprocess import PIPE
from os import path

from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import HttpResponseServerError
from django.utils.html import escape

from django.shortcuts import render

from codesearch.settings import BIN_PATH
from codesearch.settings import CODE_ROOT
from ui.util import get_repo_type

HIGHLIGHT_QUERY_TEMPLATE = r'<span class="highlighted-search-query">\1</span>'
DEEP_LINK_TEMPLATES = {
    'bitbucket': 'https://bitbucket.org/%(fully_qualified_repo_name)s/src/%(branch)s/%(fpath)s',
    'github': 'https://github.com/%(fully_qualified_repo_name)s/blob/%(branch)s/%(fpath)s',
}
LINENO_TEMPLATES = {
    'bitbucket': '%s-%s',
    'github': 'L%s',
}

E_UNABLE_TO_SEARCH = 'unable to search.'

log = logging.getLogger(__name__)

class RegexError(Exception):
    pass

class CSearchMissingError(Exception):
    pass

def index(request):
    return render(request, 'index.html')

def search(request):
    query = request.GET.get('q')
    case_sensitive = request.GET.get('case', '').lower() != 'insensitive'
    if query is None:
        return HttpResponseBadRequest()

    s = time.time()
    try:
        output = do_search(query, case_sensitive)
    except CSearchMissingError as e:
        log.error('problem executing csearch: %s', e)
        return HttpResponseServerError(E_UNABLE_TO_SEARCH)

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

    try:
        output = do_search(query, case_sensitive)
    except CSearchMissingError as e:
        log.error('problem executing csearch: %s', e)
        return render_json({'error': E_UNABLE_TO_SEARCH}, status_code=500)

    results, count, error = None, None, None
    try:
        results, count = parse_search_results(output, query, case_sensitive, html=False)
    except RegexError as e:
        error = e.message

    return render_json({'results': results, 'count': count, 'error': error})


def render_json(data, status_code=200):
    return HttpResponse(json.dumps({'data': data}), content_type="application/json", status_code=status_code)

###### to be refactored

def do_search(query, case_sensitive=True):
    # this is extremely important security code here, this
    # prevents shell code injection
    safe_query = pipes.quote(query)

    case_arg = '' if case_sensitive else '-i'
    executable = path.join(BIN_PATH, 'csearch')
    cmd = '%s -n %s %s' % (executable, case_arg, safe_query)
    log.info('cmd = %s', cmd)

    p = Popen([cmd], stdout=PIPE, stderr=PIPE, shell=True)
    out, err = p.communicate()
    log.info('csearch return code = %d', p.returncode)
    if p.returncode > 1: # not zero, see the source for csearch
        raise CSearchMissingError(err)

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

    # default_git_branches is a map of repo to default branch
    # (sproutsocial/oak => 'main')
    default_git_branches = {}

    for line in lines:
        log.debug('line=%s', line)
        fields = line.split(':', 2)  # don't split on colons that are part of source code :)
        try:
            fullpath, lineno, srcline = fields
            # codesearch's line #s are off by one
            # https://github.com/google/codesearch/issues/25
            lineno = str(long(lineno)+1)
            vcs_loc, fully_qualified_repo_name, filename, repo_type = get_repo_and_filepath(fullpath)

            if is_vcs_folder(filename):
                continue

            count += 1

            if repo_type == 'git' and not default_git_branches.has_key(fully_qualified_repo_name):
                git_dir = fullpath.split(fully_qualified_repo_name)[0] + fully_qualified_repo_name + '/.git'
                cmd = "git --git-dir %s branch" % git_dir
                p = Popen([cmd], stdout=PIPE, stderr=PIPE, shell=True)
                out, err = p.communicate()
                if p.returncode == 0:
                    log.debug("Default Branch for %s is %s" % (fully_qualified_repo_name, out.split(' ')[1].strip()))
                    default_git_branches[fully_qualified_repo_name] = out.split(' ')[1].strip()

            result = {
                'filename': filename,
                'lineno': long(lineno),
                'srcline': prepare_source_line(query_re, srcline, html),
                'deeplink': deep_link(vcs_loc, fully_qualified_repo_name, filename, repo_type, lineno, default_git_branches.get(fully_qualified_repo_name, None)),
                'count': count
            }
            if fully_qualified_repo_name not in results:
                results[fully_qualified_repo_name] = {}

            if vcs_loc not in results[fully_qualified_repo_name]:
                results[fully_qualified_repo_name][vcs_loc] = {}
                results[fully_qualified_repo_name][vcs_loc]['files'] = OrderedDict()

            if filename not in results[fully_qualified_repo_name][vcs_loc]['files']:
                results[fully_qualified_repo_name][vcs_loc]['files'][filename] = []

            results[fully_qualified_repo_name][vcs_loc]['files'][filename].append(result)
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
    relpath = path.relpath(fully_qualified_filename, CODE_ROOT)
    vcs_loc, orgname, reponame, rel_file_path = relpath.split('/', 3)
    repo_type = get_repo_type(path.join(CODE_ROOT, vcs_loc, orgname, reponame))
    return vcs_loc, '%s/%s' % (orgname, reponame), rel_file_path, repo_type


def deep_link(vcs_loc, fully_qualified_repo_name, filepath, repo_type, lineno=None, git_branch=None):
    if vcs_loc not in ('github', 'bitbucket'):
        raise ValueError('unknown vcs location: %s' % vcs_loc)

    branch = 'default' if repo_type == 'hg' else 'master'

    if git_branch:
        branch = git_branch

    fmt = DEEP_LINK_TEMPLATES[vcs_loc]
    lineno_suffix_fmt = LINENO_TEMPLATES[vcs_loc]
    src_file = path.split(filepath)[-1]
    lineno_suffix_args = (src_file, lineno) if vcs_loc == 'bitbucket' else (lineno,)

    args = {'fully_qualified_repo_name': fully_qualified_repo_name, 'fpath': filepath, 'branch': branch}
    link = fmt % args
    link += '#' + lineno_suffix_fmt % lineno_suffix_args if lineno else ''

    return link
