from charm.openstack.ip import PUBLIC, INTERNAL, ADMIN
from charm.openstack.charm import OpenStackCharmFactory, OpenStackCharm
from charm.openstack.adapters import OpenStackRelationAdapters, OpenStackRelationAdapter, ConfigurationAdapter
from charmhelpers.core.hookenv import log, config
from keystoneclient.v2_0 import client as keystoneclient
import glanceclient

class TempestAdminAdapter(OpenStackRelationAdapter):

    interface_type = "identity-admin"

    def __init__(self, relation):
        super(TempestAdminAdapter, self).__init__(relation)
        self.init_keystone_client()
        self.uconfig = config()

    def init_keystone_client(self):
        self.kc = None
        keystone_auth_url = '{}://{}:{}/v2.0'.format(
            'http',
            self.creds['service_hostname'],
            self.creds['service_port']
        )
        auth = {
            'username': self.creds['service_username'],
            'password': self.creds['service_password'],
            'auth_url': keystone_auth_url,
            'tenant_name': self.creds['service_tenant_name'],
            'region_name': self.creds['service_region'],
        }
        try:
            self.kc = keystoneclient.Client(**auth)
        except:
            log("Keystone does not appear to be ready, deferring keystone "
                "query")

    @property
    def ec2_creds(self):
        self.init_keystone_client()
        if not self.kc:
            return
        current_creds = self.kc.ec2.list(self.kc.user_id)
        if current_creds:
            creds = current_creds[0]
        else:
            creds = self.kc.ec2.create(self.kc.user_id, self.kc.tenant_id)
        return {'access_token': creds.access, 'secret_token': creds.secret}

    @property
    def image_info(self):
        glance_endpoint = self.kc.service_catalog.url_for(
            service_type='image',
            endpoint_type='publicURL')
        image_info = {}
        try:
            glance_client = glanceclient.Client(
                '2', glance_endpoint, token=self.kc.auth_token)
            for image in glance_client.images.list():
                if self.uconfig.get('glance-image-name') == image.name:
                    image_info['image_id'] = image.id
                if self.uconfig.get('glance-alt-image-name') == image.name:
                    image_info['image_alt_id'] = image.id
        except:
            log("Glance does not appear to be ready, deferring glance query")
        return image_info

    @property
    def creds(self):
        return self.relation.credentials()

    @property
    def auth_url(self):
        bob = self.get_keystone_client() or 'bugger'
        return bob



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
        'python3-cinderclient', 'python3-glanceclient', 'python3-heatclient',
        'python3-keystoneclient', 'python3-neutronclient', 'python3-novaclient',
        'python3-swiftclient', 'python3-ceilometerclient',
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

