import charms.reactive as reactive
import charm.openstack.tempest as tempest

# config is rendered when the run tempest action is called


@reactive.when_not('charm.installed')
def install_packages():
    tempest.install()
    reactive.set_state('charm.installed')


@reactive.when('charm.installed')
def assess_status():
    tempest.assess_status()
