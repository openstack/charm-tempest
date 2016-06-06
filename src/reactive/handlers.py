import charms.reactive as reactive
import charm.openstack.tempest as tempest


@reactive.when_not('charm.installed')
def install_packages():
    tempest.install()
    reactive.set_state('charm.installed')


@reactive.when('identity-admin.available')
def render_tempest_config(keystone):
    tempest.render_configs([keystone])
