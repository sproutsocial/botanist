#botanist
a web and command-line code search tool for teams.

## web search
![botanist-search-main](docs/botanist-search-main.png)

![botanist-search-results](docs/botanist-search-results.png)

## command line search
![botanist-btgrep-command-line](docs/botanist-btgrep-command-line.png)

#requirements

* an ubuntu server
* a username/password for a bitbucket.org account that has access to the repositories desired to be indexed
* a username/password or username/access_token for a github.com account that has access to repositories desired to be indexed
* apache, nginx, or any other WSGI server for the Django webapp.

#build / installation

```
make clean
make
```
This builds a tarball named `botanist.tar.gz`

untar it on the target server, cd into the directory, and run `install.sh`

You'll have to setup the webapp and start it using any webserver that supports WSGI.

The installation script sets up 2 periodic crons that run every half hour, one fetches new repositories for the team, the other re-indexes the source code.

During the installation process, it will ask you what user to run things
as, as well as for a valid bitbucket username/password. It stores this
in a file that is only readable by the user it is installed under.

#packages

##code search
https://code.google.com/p/codesearch/
(cindex running on a periodic cron to re-index)

##repository fetching
https://github.com/samkuehn/bitbucket-backup
(running on a periodic cron to update the source code to search)
NOTE: Enclosed under ./packages is a custom fork of
samkeuhn/bitbucket-backup. I've issued several PR's that he's accepted
so he is really quick and amenable to updates, I just haven't quite
finished cleaning up the additions I made recently.

##pull requests welcome! checkout the TODOs file