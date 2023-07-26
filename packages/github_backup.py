#!/usr/bin/env python
"""
Backup all your organization's repositories, private or otherwise.
"""
import argparse
import base64
import contextlib
import json
import os

from collections import namedtuple
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


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
        print("Executing command: %s" % self.redact(command))
        resp = os.system(command)
        if resp != 0:
            raise Exception(self.redact("Command [%s] failed (%s)" % (command, resp)))

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
        request =Request(url)
    elif username and password:
        url += urlencode(qs_params)
        request = Request(url)
        add_https_basic_auth(request, username, password)
    else:
        raise ValueError('unworkable combination of authentication inputs')

    response = urlopen(request)
    try:
        pagination = get_pagination(response.headers['Link'])
    except KeyError:
        print('no Link header, nothing to paginate through.')
        pagination = Pagination(None, None, None, None)

    repos = json.loads(response.read())
    for r in repos:
        if not r.get('archived'):
            yield r

    # so, this isn't the DRYest code ;-)
    while pagination.next:
        request = Request(pagination.next)
        if username and password:
            add_https_basic_auth(request, username, password)
        response = urlopen(request)
        pagination = get_pagination(response.headers['Link'])
        repos = json.loads(response.read())
        for r in repos:
            if not r.get('archived'):
                yield r


# Github API call, can authenticate via access token, or username and password
# git cloning/pulling, can authenticate via ssh key, or username & password via https

def repocsv(string):
    """
    >>> repocsv('org1/repo1, org2/repo2,org3/repo3 ,org4/repo4')
    ['org1/repo1', 'org2/repo2', 'org3/repo3', 'org4/repo4']
    """
    try:
        repos = [r.strip() for r in string.split(',')]
        return set(repos)
    except Exception as exc:
        raise argparse.ArgumentTypeError(exc.message)

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
    ssh_parser.add_argument('-i', '--ignore-list', type=repocsv, default=set(), help='add repos you dont want to fetch/index, e.g. --ignore-list org1/repo1,org2/repo2')

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
    https_parser.add_argument('-i', '--ignore-list', type=repocsv, default=set(), help='add repos you dont want to fetch/index, e.g. --ignore-list org1/repo1,org2/repo2')

    args = parser.parse_args()

    if not os.path.exists(args.directory):
        os.makedirs(args.directory)

    if args.authtype == 'ssh':
        org_repos = get_repos(args.org, args.rtype, args.access_token)
    else:
        org_repos = get_repos(args.org, args.rtype, username=args.username, password=args.password)

    h = Helpers(args)

    for repo in org_repos:
        # skip ignored repos
        if repo['full_name'] in args.ignore_list:
            print('skipping ignored repository %s' % repo['full_name'])
            continue

        # skip forks unless asked not to
        if not args.forks and repo['fork']:
            print('skipping fork repository %s' % repo['full_name'])
            continue

        destdir = os.path.join(args.directory, repo['name'])
        if args.authtype == 'ssh':
            repo_path = repo['ssh_url']
        else:
            repo_path = h.https_url_with_auth(repo['clone_url'])
        if os.path.exists(destdir):
            # pull in new commits to an already tracked repository
            print('*** updating %s... ***' % h.redact(repo_path))
            with chdir(destdir):
                try:
                    h.exec_cmd('git pull origin %s' % repo['default_branch'])
                    continue
                except Exception as e:
                    print('error: %s (repo=%s); will re-clone!' % (e, repo['name']))

        # clone the repo fresh, deleting if it already existed
        print('*** backing up %s... ***' % h.redact(repo_path))
        try:
            h.exec_cmd('rm -rf %s && git clone %s %s' % (destdir, repo_path, destdir))
        except Exception as e:
            print('error: %s' % e)
