#!/usr/bin/env bash

###################################
# reindex source code repositories
###################################

BIN=/botanist/bin
REPOS=/botanist/repos

lockfile=/var/tmp/index.lock

function log {
  echo -e "`date +"%Y-%m-%d %T %Z"` $1"
}

if ( set -o noclobber; echo "$$" > "$lockfile") 2> /dev/null; then

    trap 'rm -f "$lockfile"; exit $?' INT TERM EXIT

    chmod 600 $lockfile

    # reindex all repos
    log "Starting indexing all repositories..."
    cd $REPOS

    # index everything at once or else index can get borked
    $BIN/codesearch-0.01/cindex $REPOS

    log "Finished."
    # clean up after yourself, and release your trap
    rm -f "$lockfile"
    trap - INT TERM EXIT
else
    log "Lock Exists: $lockfile owned by $(cat $lockfile)"
fi

