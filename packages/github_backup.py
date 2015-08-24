#!/usr/bin/env python
"""
Backup all your organization's repositories, private or otherwise.
"""
import argparse
import base64
import contextlib
import json
import os
import sys
import urllib2

from collections import namedtuple
from urllib import urlencode
from urllib import quote


API_BASE = 'https://api.github.com/'
REPO_TYPE_CHOICES = ('all', 'public', 'private', 'forks', 'sources', 'member')


@contextlib.contextmanager
def chdir(dirname=None):
    curdir = os.getcwd()
    try:
        if dirname is not None:
            os.chdir(dirname)
        yield
    finally:
        os.chdir(curdir)


class Helpers(object):
    def __init__(self, args):
        self.args = args

    def exec_cmd(self, command):
        """
        Executes an external command taking into account errors and logging.
        """
        print "Executing command: %s" % self.redact(command)
        resp = os.system(command)
        if resp != 0:
            sys.exit("Command [%s] failed (%s)" % (command, resp))

    def https_url_with_auth(self, base_url):
        _, suffix = base_url.split('https://')
        return 'https://%s:%s@%s' % (quote(self.args.username), quote(self.args.password), suffix)

    def redact(self, s):
        if hasattr(self.args, 'password'):
            s = s.replace(self.args.password, 'REDACTED')
        if hasattr(self.args, 'username'):
            s = s.replace(self.args.username, 'REDACTED')
        return s


Pagination = namedtuple('Pagination', 'first prev next last')
def get_pagination(raw_link_header):
    link_map = {}
    for link, rel in (lh.split(';') for lh in raw_link_header.split(',')):
        link_map[rel.split('=')[1].strip('"')] = link.strip(' <>')
    return Pagination(*(link_map.get(f) for f in Pagination._fields))


def add_https_basic_auth(request, username, password):
    base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
    request.add_header("Authorization", "Basic %s" % base64string)


def get_repos(org, repo_type, access_token=None, username=None, password=None, per_page=25):
    """
    Paginates through all of the repositories using github's Link header.
        https://developer.github.com/v3/#link-header
    """
    url = API_BASE + 'orgs/%s/repos?' % org
    qs_params = {'type': repo_type, 'per_page': per_page}
    if access_token:
        qs_params.update({'access_token': args.access_token})
        url += urlencode(qs_params)
        request = urllib2.Request(url)
    elif username and password:
        url += urlencode(qs_params)
        request = urllib2.Request(url)
        add_https_basic_auth(request, username, password)
    else:
        raise ValueError('unworkable combination of authentication inputs')

    response = urllib2.urlopen(request)
    try:
        pagination = get_pagination(response.headers['Link'])
    except KeyError:
        print 'no Link header, nothing to paginate through.'
        pagination = Pagination(None, None, None, None)

    repos = json.loads(response.read())
    for r in repos:
        yield r

    # so, this isn't the DRYest code ;-)
    while pagination.next:
        request = urllib2.Request(pagination.next)
        if username and password:
            add_https_basic_auth(request, username, password)
        response = urllib2.urlopen(request)
        pagination = get_pagination(response.headers['Link'])
        repos = json.loads(response.read())
        for r in repos:
            yield r


# Github API call, can authenticate via access token, or username and password
# git cloning/pulling, can authenticate via ssh key, or username & password via https

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='backup github repositories for an organization')
    subparsers = parser.add_subparsers(dest='authtype')

    # uses an access token to fetch repositories names from github's API,
    # but then assumes you have SSH keys setup for cloning/pulling
    ssh_parser = subparsers.add_parser('ssh', help='use ssh for cloning/pulling, and use access token for github api access')
    ssh_parser.add_argument('-d', '--dir', type=str, dest='directory', required=True, help='full or relative path to store backed up repositories')
    ssh_parser.add_argument('-o', '--org', type=str, required=True, help='github organization name')
    ssh_parser.add_argument('-t', '--type', type=str, dest='rtype', nargs='?', default='all', choices=REPO_TYPE_CHOICES, help='repository types to backup')
    ssh_parser.add_argument('-a', '--access-token', type=str, help='personal access token or oauth access token')
    ssh_parser.add_argument('-f', '--forks', action='store_true', help='add this arg if you want to backup fork repositories also')

    # uses a username and password for fetching repositories names from
    # github's API, and uses same username and password for
    # cloning/updating via HTTPS as well.
    #
    # note: you can also use your personal access token as a password for https
    # basic auth when talking to github's api or cloning
    https_parser = subparsers.add_parser('https', help='use https for cloning/pulling, and use username and password (https basic auth) for github api access. note that github also allows using a personal access token as a password via this method')
    https_parser.add_argument('-d', '--dir', type=str, dest='directory', required=True, help='full or relative path to store backed up repositories')
    https_parser.add_argument('-o', '--org', type=str, required=True, help='github organization name')
    https_parser.add_argument('-t', '--type', type=str, dest='rtype', nargs='?', default='all', choices=REPO_TYPE_CHOICES, help='repository types to backup')
    https_parser.add_argument('-u', '--username', dest='username', type=str, required=True, help='github username')
    https_parser.add_argument('-p', '--password', dest='password', type=str, required=True, help='github password or github personal access token')
    https_parser.add_argument('-f', '--forks', action='store_true', help='add this arg if you want to backup fork repositories also')

    args = parser.parse_args()

    if not os.path.exists(args.directory):
        os.makedirs(args.directory)

    if args.authtype == 'ssh':
        org_repos = get_repos(args.org, args.rtype, args.access_token)
    else:
        org_repos = get_repos(args.org, args.rtype, username=args.username, password=args.password)

    h = Helpers(args)

    for repo in org_repos:
        # skip forks unless asked not to
        if not args.forks and repo['fork']:
            print 'skipping fork repository %s' % repo['name']
            continue
        destdir = os.path.join(args.directory, repo['name'])
        if args.authtype == 'ssh':
            repo_path = repo['ssh_url']
        else:
            repo_path = h.https_url_with_auth(repo['clone_url'])
        if os.path.exists(destdir):
            print '*** updating %s... ***' % h.redact(repo_path)
            with chdir(destdir):
                h.exec_cmd('git pull %s' % repo_path)
        else:
            print '*** backing up %s... ***' % h.redact(repo_path)
            h.exec_cmd('git clone %s %s' % (repo_path, destdir))

