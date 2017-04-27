
from charmhelpers.contrib.openstack.amulet.deployment import (
    OpenStackAmuletDeployment
)

from charmhelpers.contrib.openstack.amulet.utils import (
    OpenStackAmuletUtils,
    DEBUG,
)

# Use DEBUG to turn on debug logging
u = OpenStackAmuletUtils(DEBUG)


class TempestBasicDeployment(OpenStackAmuletDeployment):
    """Amulet tests on a basic tempest deployment."""

    def __init__(self, series, openstack=None, source=None, stable=False):
        """Deploy the entire test environment."""
        super(TempestBasicDeployment, self).__init__(series, openstack,
                                                     source, stable)
        self._add_services()
        self._add_relations()
        self._configure_services()
        self._deploy()

        u.log.info('Waiting on extended status checks...')
        exclude_services = []
        self._auto_wait_for_status(exclude_services=exclude_services)

        self.d.sentry.wait()
        self._initialize_tests()

    def _add_services(self):
        """Add services

           Add the services that we're testing, where tempest is local,
           and the rest of the service are from lp branches that are
           compatible with the local charm (e.g. stable or next).
           """
        this_service = {'name': 'tempest'}
        other_services = [
            {'name': 'percona-cluster', 'constraints': {'mem': '3072M'}},
            {'name': 'rabbitmq-server'},
            {'name': 'keystone'},
            {'name': 'openstack-dashboard'},
            {'name': 'glance'}
        ]
        super(TempestBasicDeployment, self)._add_services(
            this_service,
            other_services,
            no_origin=['tempest'])

    def _add_relations(self):
        """Add all of the relations for the services."""
        relations = {
            'keystone:identity-admin': 'tempest:identity-admin',
            'tempest:dashboard': 'openstack-dashboard:website',
            'openstack-dashboard:identity-service':
            'keystone:identity-service',
            'keystone:shared-db': 'percona-cluster:shared-db',
            'glance:identity-service': 'keystone:identity-service',
            'glance:shared-db': 'percona-cluster:shared-db',
            'glance:amqp': 'rabbitmq-server:amqp'
        }
        super(TempestBasicDeployment, self)._add_relations(relations)

    def _configure_services(self):
        """Configure all of the services."""
        keystone_config = {'admin-password': 'openstack',
                           'admin-token': 'ubuntutesting'}
        pxc_config = {
            'dataset-size': '25%',
            'max-connections': 1000,
            'root-password': 'ChangeMe123',
            'sst-password': 'ChangeMe123',
        }
        configs = {
            'keystone': keystone_config,
            'percona-cluster': pxc_config,
        }
        super(TempestBasicDeployment, self)._configure_services(configs)

    def _get_token(self):
        return self.keystone.service_catalog.catalog['token']['id']

    def _initialize_tests(self):
        """Perform final initialization before tests get run."""
        # Access the sentries for inspecting service units
        self.tempest_sentry = self.d.sentry['tempest'][0]
        self.openstack_dashboard_sentry = \
            self.d.sentry['openstack-dashboard'][0]
        u.log.debug('openstack release val: {}'.format(
            self._get_openstack_release()))
        u.log.debug('openstack release str: {}'.format(
            self._get_openstack_release_string()))

    def test_run_tempest(self):
        u.log.debug('Running Tempest...')
        unit = self.tempest_sentry
        assert u.status_get(unit)[0] == "active"

        action_id = u.run_action(unit, "run-tempest")
        assert u.wait_on_action(action_id), "run-tempest action failed."
