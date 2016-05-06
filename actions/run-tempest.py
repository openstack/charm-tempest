#!/usr/bin/env python3

import os
import subprocess
import sys
import time
sys.path.append('lib')

import charm.openstack.tempest as tempest
import charms.reactive as reactive
import charmhelpers.core.hookenv as hookenv
import charmhelpers.fetch as fetch


def setup_git(branch, git_dir, tempest_conf):
    """Clone tempest and symlink in rendered tempest.conf"""
    conf = hookenv.config()
    if not os.path.exists(git_dir):
        git_url = conf['tempest-source']
        fetch.install_remote(str(git_url), dest=str(git_dir),
                             branch=str(branch), depth=str(1))
    conf_symlink = git_dir + '/tempest/etc/tempest.conf'
    if not os.path.exists(conf_symlink):
        os.symlink(tempest_conf, conf_symlink)


def execute_tox(run_dir, logfile, tox_target):
    """Trigger tempest run through tox setting proxies if needed"""
    env = os.environ.copy()
    conf = hookenv.config()
    if conf.get('http-proxy'):
        env['http_proxy'] = conf['http-proxy']
    if conf.get('https-proxy'):
        env['https_proxy'] = conf['https-proxy']
    cmd = ['tox', '-e', tox_target]
    f = open(logfile, "w")
    subprocess.call(cmd, cwd=run_dir, stdout=f, stderr=f)


def get_tempest_files(branch_name):
    """Prepare tempets files and directories

    @return git_dir, logfile, run_dir
    """
    log_time_str = time.strftime("%Y%m%d%H%M%S", time.gmtime())
    git_dir = '{}/tempest-{}'.format(
        tempest.TempestCharm.TEMPEST_ROOT,
        branch_name
    )
    logfile = '{}/run_{}.log'.format(
        tempest.TempestCharm.TEMPEST_LOGDIR,
        log_time_str
    )
    run_dir = git_dir + '/tempest'
    return git_dir, logfile, run_dir


def run_test(tox_target):
    """Run smoke tests"""
    action_args = hookenv.action_get()
    branch_name = action_args['branch']
    tempest_git_dir, tempest_logfile, run_dir = get_tempest_files(branch_name)
    action_info = {
        'tempest-logfile': tempest_logfile,
    }
    setup_git(branch_name, tempest_git_dir, tempest.TempestCharm.TEMPEST_CONF)
    execute_tox(run_dir, tempest_logfile, tox_target)
    hookenv.action_set(action_info)


if __name__ == '__main__':
    # Cloud may have different artifacts (flavors, images etc) since last run
    # so rerun handlers file to regenerate config.
    reactive.main()
    run_test('smoke')
