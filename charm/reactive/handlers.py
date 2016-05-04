import charms.reactive as reactive
import charm.openstack.tempest as tempest
import charmhelpers.contrib.openstack.utils as ch_utils
import os

charm = None

def get_charm():
    global charm
    if charm is None:
        charm = tempest.TempestCharmFactory.charm()
    return charm

@reactive.hook('install')
def install_packages():
    get_charm().install()

@reactive.when('identity-admin.connected')
def render_tempest_config(keystone):
    charm = tempest.TempestCharmFactory.charm(
        interfaces=[keystone]
    )
    if not os.path.isdir(charm.TEMPEST_LOGDIR):
        os.makedirs(charm.TEMPEST_LOGDIR)
    charm.render_all_configs()
