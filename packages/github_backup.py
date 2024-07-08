#!/venv/bin/python3
"""
Backup all your organization's repositories, private or otherwise.
"""

import sentry_sdk
sentry_sdk.init()

import argparse
import base64
import contextlib
import json
import logging
import os
import subprocess

from datadog import initialize, statsd
from collections import namedtuple
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


API_BASE = 'https://api.github.com/'
REPO_TYPE_CHOICES = ('all', 'public', 'private', 'forks', 'sources', 'member')

initialize()

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
        logging.info("Executing command: %s" % self.redact(command))
        try:
            command_output = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True, encoding='UTF-8')
            logging.debug("Output of command: \n%s", self.redact(command_output))
        except subprocess.CalledProcessError as e:
            logging.warning("Output of failed command: \n%s", self.redact(e.output))
            if e.returncode < 0:
                msg = f"Child was terminated by signal {-e.returncode}"
            else:
                msg = f"Child returned {e.returncode}"
            raise Exception(self.redact("Command [%s] failed: %s" % (command, msg)))
        except OSError as e:
            raise Exception(self.redact("Command [%s] failed: %s" % (command, e)))

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


def add_https_basic_auth(request: Request, username, password):
    base64string = base64.b64encode(f'{username}:{password}'.encode('utf-8'))
    request.add_header("Authorization", "Basic %s" % base64string.decode('utf-8'))


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
        request = Request(url)
    elif username and password:
        url += urlencode(qs_params)
        request = Request(url)
        add_https_basic_auth(request, username, password)
    else:
        raise ValueError('unworkable combination of authentication inputs')

    response = urlopen(request)
    raw_link_header = response.headers.get('Link')
    if raw_link_header is None:
        logging.debug('no Link header, nothing to paginate through.')
        pagination = Pagination(None, None, None, None)
    pagination = get_pagination(raw_link_header)

    repos = json.loads(response.read())
    for r in repos:
        if not r.get('archived'):
            yield r
        else:
            logging.info(f'skipping archived repository {r["full_name"]}')

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
            else:
                logging.info(f'skipping archived repository {r["full_name"]}')


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
    logging.basicConfig(level=os.environ.get('LOG_LEVEL', 'INFO'))
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
            logging.info('skipping ignored repository %s' % repo['full_name'])
            continue

        # skip forks unless asked not to
        if not args.forks and repo['fork']:
            logging.info('skipping fork repository %s' % repo['full_name'])
            continue

        destdir = os.path.join(args.directory, repo['name'])
        if args.authtype == 'ssh':
            repo_path = repo['ssh_url']
        else:
            repo_path = h.https_url_with_auth(repo['clone_url'])
        if os.path.exists(destdir):
            # pull in new commits to an already tracked repository
            logging.info('*** updating %s... ***' % h.redact(repo_path))
            with chdir(destdir):
                try:
                    h.exec_cmd('git pull origin %s' % repo['default_branch'])
                    statsd.increment('spt.codesearcher.git.backups', tags=[f"repo:{repo['name']}", f"branch:{repo['default_branch']}"])
                    continue
                except Exception as e:
                    logging.warning(f'error pulling {repo["name"]}, will re-clone: {e}')

        # either there is no backup of this repo yet, or the git pull failed so we want to attempt a fresh clone
        logging.info('*** full clone of %s... ***' % h.redact(repo_path))
        try:
            # Clone into a temporary path just in case the clone fails for ephemeral reasons, such as a github outage
            # This way we don't blow away the existing backup if there is one and pull may work again later
            h.exec_cmd(f'rm -rf {destdir}.tmp && git clone {repo_path} {destdir}.tmp && rm -rf {destdir} && mv {destdir}.tmp {destdir}')
            statsd.increment('spt.codesearcher.git.backups', tags=[f"repo:{repo['name']}", f"branch:{repo['default_branch']}"])
        except Exception as e:
            logging.error(f'error doing full clone of {repo["name"]}: {e}')
            # Clean up the tempdir if it got left behind
            h.exec_cmd(f'rm -rf {destdir}.tmp')
