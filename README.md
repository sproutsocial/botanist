# botanist
a web and command-line code search tool for teams.

## Web search
![botanist-search-main](docs/botanist-search-main.png)

![botanist-search-results](docs/botanist-search-results.png)

## Command-line search
![botanist-btgrep-command-line](docs/botanist-btgrep-command-line.png)

# Packages

some software packages are included to make this work. they are included
in this repository for now for compatibility purposes.

## Code search
The fast searching is made possible by the excellent codesearch tool
from Google:

https://code.google.com/p/codesearch/
(cindex running on a periodic cron to re-index)

## Bitbucket repository fetching
https://github.com/samkuehn/bitbucket-backup
(running on a periodic cron to update the source code to search)
NOTE: Enclosed under ./packages is a custom fork of
samkeuhn/bitbucket-backup. I've issued several PR's that he's accepted
so he is really quick and amenable to updates, I just haven't quite
finished cleaning up the additions I made recently.

## GitHub repository fetching
wrote up something to do this in Python based on
https://github.com/celeen/gitter

The default GitHub branch name is "main".

## Pull requests welcome!

# Running locally using docker

## 1. Create location for repositories on disk
```
mkdir -p $HOME/botanist/repos
```

## 2. Set up credentials

```
# copy env file to env.local, and set GH_USER, GH_ORGS, GH_PW so you can fetch code to index
# GH_PW should be a personal access token with repo scope
# if the org you want to back up uses SSO, you also need to authorize the token to the org
# under "Configure SSO"
cp env.template env.local
```

## 3. Start botanist

```
docker-compose stop && docker-compose rm -f && docker-compose up --build -d
```

## 4. Fetch code repositories using the image you just built

```
docker run --env-file env.local -v $HOME/botanist/repos:/botanist/repos botanist-webapp /botanist/bin/fetch-code.sh
```

## 5. Index the code repositories using the image you just built

```
docker run --env-file env.local -v $HOME/botanist/repos:/botanist/repos botanist-webapp /botanist/bin/index.sh
```
