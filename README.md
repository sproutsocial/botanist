#botanist
a web-based code search tool

##requirements

* an ubuntu server
* a username/password for a bitbucket.org account that has access to the repositories desired

##build / installation

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

##packages

###code search
https://code.google.com/p/codesearch/
(cindex running on a periodic cron to re-index)

###repository fetching
https://github.com/samkuehn/bitbucket-backup
(running on a periodic cron to update the source code to search)
NOTE: Enclosed under ./packages is a custom fork of
samkeuhn/bitbucket-backup. I've issued several PR's that he's accepted
so he is really quick and amenable to updates, I just haven't quite
finished cleaning up the additions I made recently.

##pull requests welcome! checkout the TODOs file

## usages
### web
self explanatory, you can search code via the web ui
### spgrep.py command line utility
Provides a grep-like interface to the JSON api of the web service, e.g.

```
$ ./spgrep.py -h
usage: spgrep.py [-h] [-i] PATTERN

positional arguments:
  PATTERN            regex pattern you wish to search for

optional arguments:
  -h, --help         show this help message and exit
  -i, --ignore-case  Ignore case distinctions
```

```
$ ./spgrep.py "class HeartbeaterImpl"
heartbeater:src/main/java/heartbeater/HeartbeaterImpl.java:24:public class HeartbeaterImpl implements Heartbeater{
heartbeater:src/test/java/heartbeater/HeartbeaterImplTest.java:34:public class HeartbeaterImplTest {
```
