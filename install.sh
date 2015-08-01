#!/usr/bin/env bash

echo -e -n "\nEnter username to run as / install under: "
read USER
INSTALL_DIR=/home/$USER/botanist

# get required os packages
# only works on ubuntu
sudo apt-get update --fix-missing --assume-yes
sudo apt-get install mercurial git python-virtualenv --assume-yes

cd $INSTALL_DIR

BIN=$INSTALL_DIR/bin
mkdir -p $BIN
CRON=$INSTALL_DIR/cron
mkdir -p $CRON
LOGS=$INSTALL_DIR/logs
mkdir -p $LOGS
PACKAGES=$INSTALL_DIR/packages
mkdir -p $PACKAGES
REPOS=$INSTALL_DIR/repos
mkdir -p $REPOS/bitbucket
mkdir -p $REPOS/github
WEBAPP=$INSTALL_DIR/webapp
mkdir -p $WEBAPP

####################################################
# install packages
####################################################

# unpack and install codesearch
cd packages
tar zxf codesearch-0.01-linux-amd64.tgz
mv ./codesearch-0.01/cindex $BIN/cindex
mv ./codesearch-0.01/cgrep $BIN/cgrep
mv ./codesearch-0.01/csearch $BIN/csearch

# unpack and install bitbucket backup
# its not really a proper packaged bin file but
# oh well this'll do for now
tar zxf bitbucket-backup.tgz
mv ./bitbucket-backup $BIN

# unpack and install github backup
mv ./github_backup.py $BIN

####################################################
# configure fetch-code.sh cron
####################################################
cd $INSTALL_DIR
echo -e "\n"
read -r -p "Do you wish to connect to bitbucket? [y/N] " bbanswer
if [[ $bbanswer == 'y' ]]; then
	echo -n "Enter the bitbucket.org username : "
	read bbusername
	echo -n "Enter the bitbucket.org password : "
	read -s bbpassword
	echo -e -n "\nEnter the bitbucket.org team/org : "
	read bbteam
	sed -i \
	    -e "s/%RUNASUSER%/$USER/" \
    	-e "s/%BB_USERNAME%/$bbusername/" \
    	-e "s/%BB_PASSWORD%/$bbpassword/" \
    	-e "s/%BB_TEAM%/$bbteam/" \
    	-e "s/%USE_BB%/true/" \
    	$CRON/fetch-code.sh.template
fi

read -r -p "Do you wish to connect to github? [y/N]" ghanswer
if [[ $ghanswer == 'y' ]]; then
	echo -n "Enter the github.com username : "
	read ghusername
	echo -n "Enter the github.com password or access token : "
   read -s ghpassword
	echo -e -n "\nEnter the github.com team/org : "
   read ghorg
	sed -i \
	    -e "s/%RUNASUSER%/$USER/" \
    	-e "s/%GH_USERNAME%/$ghusername/" \
    	-e "s/%GH_PASSWORD%/$ghpassword/" \
    	-e "s/%GH_ORG%/$ghorg/" \
    	-e "s/%USE_GH%/true/" \
    	$CRON/fetch-code.sh.template
fi

mv $CRON/fetch-code.sh.template $CRON/fetch-code.sh
chmod 700 $CRON/fetch-code.sh

####################################################
# configure index.sh cron
####################################################
sed -e "s/%RUNASUSER%/$USER/" \
    $CRON/index.sh.template > $CRON/index.sh
chmod 700 $CRON/index.sh
rm $CRON/index.sh.template

####################################################
# install crons
####################################################
# code fetching cron every half hour
line="*/30 * * * * $CRON/fetch-code.sh > $LOGS/fetch-code.log"
(crontab -u $USER -l; echo "$line" ) | crontab -u $USER -

# search index cron, every half hour
line="*/30 * * * * $CRON/index.sh > $LOGS/index.log"
(crontab -u $USER -l; echo "$line" ) | crontab -u $USER -

echo -e "crons installed:\n"
crontab -l

####################################################
# kickoff code fetch for first time in background
# lockfile will prevent crontab from double executing
####################################################
echo -e "starting initial fetching of code in the background...\n"
nohup $CRON/fetch-code.sh 2>&1 >> $LOGS/fetch-code.log &

####################################################
# kickoff cindex for first time in background on a
# small delay so it has something to index
####################################################
echo -e "initial index run will commence in 1 minute...\n"
( sleep 60; nohup $CRON/index.sh 2>&1 >> $LOGS/index.log ) &

###################
# install webapp
###################
cd $WEBAPP
virtualenv .env
. .env/bin/activate
pip install -r requirements.txt
touch $WEBAPP/webapp.conf
sed -e "s#%CODEROOT%#$REPOS#" \
    -e "s#%BINPATH%#$BIN#" \
    -e "s#%BB_TEAM%#$bbteam#" \
    -e "s#%GH_ORG%#$ghorg#" \
    $WEBAPP/webapp.conf.template > $WEBAPP/webapp.conf
