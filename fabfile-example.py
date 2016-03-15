from fabric.context_managers import cd
from fabric.context_managers import lcd
from fabric.decorators import task
from fabric.operations import local
from fabric.operations import put
from fabric.operations import sudo
from fabric.state import env

# Super simple deployment script. Assumes you've placed apache2 in front of it
# Just setup:
#
#   env.hosts -- where you deploy
#   ROOT_PATH -- the dir you installed botanist
#   USER -- the user you installed botanist under


env.colorize_errors = True
env.use_ssh_config = True  # super handy, uses your ~/.ssh/config
env.hosts = ['TBD']

ROOT_PATH = '/srv/botanist'
USER = 'botanist'


@task
def deploy_webapp():
    with lcd('webapp'):
        local('find . -name "*.pyc" -exec rm {} \;')
    local('tar --exclude=webapp/.idea --exclude=webapp/.venv --exclude=webapp/atlassian-ide-plugin.xml --exclude=webapp/*.conf -czf webapp.tar.gz webapp/')
    with cd(ROOT_PATH):
        put('webapp.tar.gz', '.', use_sudo=True)
        sudo('tar zxvf webapp.tar.gz', user=USER, group=USER)
        sudo('rm -rf webapp.tar.gz', user=USER, group=USER)
    local('rm webapp.tar.gz')
    sudo('service apache2 restart')
