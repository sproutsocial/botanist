from os.path import isdir
from os.path import join


def get_repo_type(filepath):
    if isdir(join(filepath, ".git")):
        return "git"
    elif isdir(join(filepath, ".hg")):
        return "hg"
    else:
        raise ValueError("no git or hg repo found at %s" % filepath)
