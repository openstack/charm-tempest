import charms.reactive as reactive
import charm.openstack.tempest as tempest
import os


@reactive.hook('install')
def install_packages():
    tempest.get_charm().install()


@reactive.when('identity-admin.available')
def render_tempest_config(keystone):
    charm = tempest.TempestCharmFactory.charm(
        interfaces=[keystone]
    )
    if not os.path.isdir(charm.TEMPEST_LOGDIR):
        os.makedirs(charm.TEMPEST_LOGDIR)
    charm.render_all_configs()
