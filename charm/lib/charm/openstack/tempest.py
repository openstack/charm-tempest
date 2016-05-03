from charm.openstack.ip import PUBLIC, INTERNAL, ADMIN
from charm.openstack.charm import OpenStackCharmFactory, OpenStackCharm
from charm.openstack.adapters import OpenStackRelationAdapters, OpenStackRelationAdapter, ConfigurationAdapter

class TempestAdminAdapter(OpenStackRelationAdapter):

    interface_type = "identity-admin"

    def __init__(self, relation):
        super(TempestAdminAdapter, self).__init__(relation)

    @property
    def creds(self):
        return self.relation.credentials()


class TempestAdapters(OpenStackRelationAdapters):
    """
    Adapters class for the Designate charm.
    """
    relation_adapters = {
        'identity_admin': TempestAdminAdapter,
    }

    def __init__(self, relations):
        super(TempestAdapters, self).__init__(
            relations,
            options=TempestConfigurationAdapter)

class TempestConfigurationAdapter(ConfigurationAdapter):

    def __init__(self):
        super(TempestConfigurationAdapter, self).__init__()

    @property
    def nova_base(self):
        return 'bob'


class TempestCharm(OpenStackCharm):

    TEMPEST_ROOT = '/var/lib/tempest/'
    TEMPEST_LOGDIR = TEMPEST_ROOT + '/logs'
    TEMPEST_CONF = TEMPEST_ROOT + '/tempest.conf'
    PIP_CONF = '/root/.pip/pip.conf'

    packages = [
        'git', 'testrepository', 'subunit', 'python-nose', 'python-lxml',
        'python-boto', 'python-junitxml', 'python-subunit',
        'python-testresources', 'python-oslotest', 'python-stevedore',
        'python-cinderclient', 'python-glanceclient', 'python-heatclient',
        'python-keystoneclient', 'python-neutronclient', 'python-novaclient',
        'python-swiftclient', 'python-ceilometerclient', 'openvswitch-test',
        'openvswitch-common', 'libffi-dev', 'libssl-dev', 'python-dev',
        'python-cffi'
    ]

    adapters_class = TempestAdapters
    restart_map = {
        TEMPEST_CONF: [],
        PIP_CONF: [],
    }

class TempestCharmFactory(OpenStackCharmFactory):

    releases = {
        'liberty': TempestCharm
    }

    first_release = 'liberty'

