#!/usr/bin/env python

import argparse
import json
import sys
import urllib
import urllib2
import base64

BOTANIST_DOMAIN = 'https://codesearcher.int.sproutsocial.com/'
# NOTE: Fill out with real username/password to test.
# (Or come up with a real solution like sticking an auth-less version behind SDM)
LDAP_USERNAME = ''
LDAP_PASSWORD = ''


def get_vcs_prefix(vcs_loc):
    if vcs_loc == 'bitbucket':
        return 'bb'
    elif vcs_loc == 'github':
        return 'gh'
    else:
        raise ValueError('unknown vcs_loc: %s' % vcs_loc)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("PATTERN", help="regex pattern you wish to search for")
    parser.add_argument("-i", "--ignore-case", help="Ignore case distinctions", action="store_true")
    args = parser.parse_args()

    params = urllib.urlencode({'q': args.PATTERN, 'case': 'insensitive' if args.ignore_case else 'sensitive'})
    req = urllib2.Request(BOTANIST_DOMAIN + '/search/results.json?' + params)
    req.add_header('Authorization', 'Basic {0}'.format(
        base64.encodestring('{0}:{1}'.format(
            LDAP_USERNAME, LDAP_PASSWORD))[:-1]))
    resp = urllib2.urlopen(req).read()
    data = json.loads(resp).get('data', {}).get('results', {})

    if data is None:
        print 'no results found.'
        sys.exit(1)

    for reponame in sorted(data.keys()):
        for vcs_loc, repo_result_dict in data[reponame].items():
            files = repo_result_dict['files']
            for filename in sorted(files.keys()):
                for srcline_obj in files[filename]:
                    srcline = srcline_obj.get('srcline')
                    if srcline is None:
                        continue
                    lineno = srcline_obj.get('lineno')
                    if lineno is None:
                        continue

                    print '%s:%s:%s:%s:%s' % (get_vcs_prefix(vcs_loc), reponame.encode('utf-8'), filename.encode('utf-8'), lineno, srcline.encode('utf-8'))
