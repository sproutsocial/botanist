#!/usr/bin/env python

import argparse
import json
import sys
import urllib
import urllib2

# You need to fill in the domain of where you install
# Botanist for this to work, obviously :)
BOTANIST_DOMAIN = 'http://example.com'


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
    r = urllib2.urlopen(BOTANIST_DOMAIN + '/search/results.json?' + params).read()
    data = json.loads(r).get('data', {}).get('results', {})

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
