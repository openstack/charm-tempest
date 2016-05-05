#!/usr/bin/env python3

import sys
sys.path.append('lib')

import os
import subprocess
from charmhelpers.core.hookenv import (
    action_set,
    config,
    action_get,
)
from time import gmtime, strftime
import charm.openstack.tempest as tempest
from charmhelpers.fetch import install_remote


def setup_git(branch, git_dir, tempest_conf):
    conf = config()
    if not os.path.exists(git_dir):
        git_url = conf['tempest-source']
        install_remote(str(git_url), dest=str(git_dir), branch=str(branch),
                       depth=str(1))
    conf_symlink = git_dir + '/tempest/etc/tempest.conf'
    if not os.path.exists(conf_symlink):
        os.symlink(tempest_conf, conf_symlink)


def execute_tox(run_dir, logfile):
    env = os.environ.copy()
    conf = config()
    if conf.get('http-proxy'):
        env['http_proxy'] = conf['http-proxy']
    if conf.get('https-proxy'):
        env['https_proxy'] = conf['https-proxy']
    cmd = ['tox', '-e', 'smoke']
    f = open(logfile, "w")
    subprocess.call(cmd, cwd=run_dir, stdout=f, stderr=f)


def run_smoke_test():
    action_args = action_get()
    branch = action_args['branch']
    log_time_str = strftime("%Y%m%d%H%M%S", gmtime())
    tempest_git_dir = '{}/tempest-{}'.format(
        tempest.TempestCharm.TEMPEST_ROOT,
        branch
    )
    tempest_logfile = '{}/run_{}.log'.format(
        tempest.TempestCharm.TEMPEST_LOGDIR,
        log_time_str
    )
    action_info = {
        'tempest-logfile': tempest_logfile,
    }
    run_dir = tempest_git_dir + '/tempest'
    setup_git(branch, tempest_git_dir, tempest.TempestCharm.TEMPEST_CONF)
    execute_tox(run_dir, tempest_logfile)
    action_set(action_info)


if __name__ == '__main__':
    run_smoke_test()
