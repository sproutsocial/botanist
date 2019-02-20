# botanist
a web and command-line code search tool for teams.

## web search
![botanist-search-main](docs/botanist-search-main.png)

![botanist-search-results](docs/botanist-search-results.png)

## command line search
![botanist-btgrep-command-line](docs/botanist-btgrep-command-line.png)

# important note
Botanist is now built to be deployed to a host via docker containers.

See the docker instructions [section](#docker-instructions) below.

# requirements

* an ubuntu server
* credentials for a user that has access to the repositories desired to be indexed (bitbucket.org and/or github.com) see: [Machine User](https://developer.github.com/guides/managing-deploy-keys/#machine-users)
* apache, nginx, or any other WSGI server for the Django webapp.

# build / installation

build and upload to target server:

```
make
scp target/botanist.tar.gz dest-server:
```

untar it on the target server, cd into the directory, and run `install.sh`

```
tar zxvf botanist.tar.gz
cd botanist
./install.sh

```

Installation will setup 2 crons…
will also kick off initial fetch-code and index jobs
you can start up the django web app if you want to just check it out quickly by doing:

```
cd webapp/
. .env/bin/activate
./manage.py runserver 0.0.0.0:8000
```

Then you can visit [http://localhost:8000](http://localhost:8000) to start searching!

Of course, Django's test server won't really work in production, so you'll have to setup the webapp to run using your favorite webserver that supports WSGI (Apache, Nginx, Gunicorn, etc.)

TODO: need to reorder this...
The installation script sets up 2 periodic crons that run every half hour:

* one fetches new repositories or pulls the latest commits from bitbucket and/or github
* the other (re)indexes the source code using `cindex`

During the installation process, it will ask you what user to run things
as, as well as bitbucket and/or github credentials. It stores these
in a file that is only readable by the user it is installed under.

# packages

some software packages are included to make this work. they are included
in this repository for now for compatibility purposes.

## code search
The fast searching is made possible by the excellent codesearch tool
from Google:

https://code.google.com/p/codesearch/
(cindex running on a periodic cron to re-index)

## bitbucket repository fetching
https://github.com/samkuehn/bitbucket-backup
(running on a periodic cron to update the source code to search)
NOTE: Enclosed under ./packages is a custom fork of
samkeuhn/bitbucket-backup. I've issued several PR's that he's accepted
so he is really quick and amenable to updates, I just haven't quite
finished cleaning up the additions I made recently.

## github repository fetching
wrote up something to do this in Python based on
https://github.com/celeen/gitter

## pull requests welcome!

# docker instructions

## running locally
### 

Create a folder somewhere on the host or your local laptop where the code repositories will be stored.

```
# create location for repositories on disk
mkdir -p $HOME/botanist/repos
```

```# copy env file to env.local, and
# set GH_USER, GH_ORGS, GH_PW so you can fetch code to index
cp env.template env.local
```

Make sure you generate a snakeoil SSL certificate...**DO NOT USE IN PRODUCTION**

```
$  openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout ./cert/server.key -out ./cert/server.crt
Generating a 2048 bit RSA private key
.+++
.........................................................+++
writing new private key to './cert/server.key'
-----
You are about to be asked to enter information that will be incorporated
into your certificate request.
What you are about to enter is what is called a Distinguished Name or a DN.
There are quite a few fields but you can leave some blank
For some fields there will be a default value,
If you enter '.', the field will be left blank.
-----
Country Name (2 letter code) []:US
State or Province Name (full name) []:
Locality Name (eg, city) []:
Organization Name (eg, company) []:
Organizational Unit Name (eg, section) []:
Common Name (eg, fully qualified host name) []:
Email Address []:

```

then start everything up!
```
docker-compose -f docker-compose.yml rm -f && docker-compose -f docker-compose.yml up --build
```

You can authenticate by using the `test` LDAP user who's password is `t3st`, which is created upon startup when running `docker-compose.local.yml` via the `ldapinit` container described in `Dockerfile.ldapinit`.

*NOTE* you can login by going to https://localhost and login as test:t3st

# fetch code repositories using the latest image you just built
docker run --env-file env.local -v $HOME/botanist/repos:/botanist/repos botanist_web /botanist/bin/fetch-code.sh

# index the code repositories using the image you just built
docker run --env-file env.local -v $HOME/botanist/repos:/botanist/repos botanist_web /botanist/bin/index.sh

```

### create a viable `env` file

TODO:

### periodically fetch new commits/repositories

In order to ensure the search index includes all the latest changes to your org's repositories, this should be done periodically (either via cron on the host machine or a `CronJob` in Kubernetes). I recommend re-fetching ~once every hour.

```
docker run --env-file env -v $HOME/botanist/repos:/botanist/repos botanist /botanist/bin/fetch-code.sh
```

### periodically (re-)index code
The search index must be updated after new code is fetched. This should also be run periodically (either via cron on the host machine or a `CronJob` in Kubernetes), at a frequency similar to fetching code.

```
docker run --env-file env -v $HOME/botanist/repos:/botanist/repos botanist /botanist/bin/index.sh
```

### deploy the webapp and nginx

These must be run on the same host machine (or with access to the same persistent volume) as the fetch and index periodic jobs run on.

Note: This uses nginx configured with LDAP for authentication and SSL.