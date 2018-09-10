#!/usr/bin/env bash

BIN=/botanist/bin
REPOS=/botanist/repos

############################
# bitbucket.org
############################
BITBUCKET=$REPOS/bitbucket
# bitbucket creds
# NOTE: you'll need to have ssh keys setup in order to update repos...
# *OR* use http for everything (see $USE_HTTP)

############################
# github.com
############################
GITHUB=$REPOS/github

lockfile=/var/tmp/fetch-code.lock

function log {
  echo -e "$(date +"%Y-%m-%d %T %Z") $1"
}

if ( set -o noclobber; echo "$$" > "$lockfile") 2> /dev/null; then
    echo "Starting..."

    trap 'rm -f "$lockfile"; exit $?' INT TERM EXIT
    chmod 600 $lockfile

    if [[ $USE_BB == "true" ]]; then

        log "Starting fetching/updating bitbucket.org repositories..."


        IFS=',' read -ra ADDR <<< "$BB_TEAMS"
        for BBO in "${ADDR[@]}"; do
            echo "fetching for org $BBO..."
            if [ -n "$BB_IGNORE_REPO_LIST" ]; then
                $BIN/bitbucket-backup/backup.py $BB_USE_HTTP -u $BB_USER -l $BITBUCKET/$BBO -p $BB_PW -t $BBO -v --ignore-repo-list $IGNORE_REPO_LIST 2>&1
            else
                $BIN/bitbucket-backup/backup.py $BB_USE_HTTP -u $BB_USER -l $BITBUCKET/$BBO -p $BB_PW -t $BBO -v 2>&1
            fi
        done

    fi

    if [[ $USE_GH == "true" ]]; then

        log "Starting fetching/updating github.com repositories..."

        IFS=',' read -ra ADDR <<< "$GH_ORGS"
        for GHO in "${ADDR[@]}"; do
            echo "fetching for org $GHO..."
            $BIN/github_backup.py https -u $GH_USER -p $GH_PW -o $GHO -d $GITHUB/$GHO 2>&1
        done


    fi

    log "Finished."

    # clean up after yourself, and release your trap
    rm -f "$lockfile"
    trap - INT TERM EXIT

else
    log "Lock Exists: $lockfile owned by $(cat $lockfile)"
fi


