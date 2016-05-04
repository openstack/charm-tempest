from urllib.parse import urlparse
from charm.openstack.ip import PUBLIC, INTERNAL, ADMIN
from charm.openstack.charm import OpenStackCharmFactory, OpenStackCharm
from charm.openstack.adapters import OpenStackRelationAdapters, OpenStackRelationAdapter, ConfigurationAdapter
from charmhelpers.core.hookenv import log, config
from keystoneclient.v2_0 import client as keystoneclient
import glanceclient
from neutronclient.v2_0 import client as neutronclient
from novaclient import client as novaclient

class TempestAdminAdapter(OpenStackRelationAdapter):

    interface_type = "identity-admin"

    def __init__(self, relation):
        super(TempestAdminAdapter, self).__init__(relation)
        self.init_keystone_client()
        self.uconfig = config()

    def init_keystone_client(self):
        self.kc = None
        self.keystone_auth_url = '{}://{}:{}/v2.0'.format(
            'http',
            self.creds['service_hostname'],
            self.creds['service_port']
        )
        auth = {
            'username': self.creds['service_username'],
            'password': self.creds['service_password'],
            'auth_url': self.keystone_auth_url,
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
            return {}
        current_creds = self.kc.ec2.list(self.kc.user_id)
        if current_creds:
            creds = current_creds[0]
        else:
            creds = self.kc.ec2.create(self.kc.user_id, self.kc.tenant_id)
        return {'access_token': creds.access, 'secret_token': creds.secret}

    @property
    def image_info(self):
        self.init_keystone_client()
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
    def network_info(self):
        self.init_keystone_client()
        neutron_ep = self.kc.service_catalog.url_for(
            service_type='network',
            endpoint_type='publicURL')
        network_info = {}
        try:
            neutron_client = neutronclient.Client(
                endpoint_url=neutron_ep,
                token=self.kc.auth_token)
            routers = neutron_client.list_routers(
                name=self.uconfig['router-name'])
            if len(routers['routers']) == 0:
                log("Router not found")
            else:
                router = routers['routers'][0]
                network_info['router_id'] = router['id']
            networks = neutron_client.list_networks(
                name=self.uconfig['network-name'])
            if len(networks['networks']) == 0:
                log("network not found")
            else:
                network = networks['networks'][0]
                network_info['public_network_id'] = network['id']
        except:
            log("Neutron does not appear to be ready, deferring neutron query")
        return network_info

    @property
    def compute_info(self):
        self.init_keystone_client()
        nova_ep = self.kc.service_catalog.url_for(
            service_type='compute',
            endpoint_type='publicURL'
        )
        compute_info = {}
        compute_info['nova_endpoint'] = nova_ep
        url = urlparse(nova_ep)
        compute_info['nova_base'] = '{}://{}'.format(url.scheme,
                                                     url.netloc.split(':')[0])
        try:
            nova_client = novaclient.Client(
                2,
                self.creds['service_username'],
                self.creds['service_password'],
                self.creds['service_tenant_name'],
                self.keystone_auth_url,
            )
            for flavor in nova_client.flavors.list():
                if self.uconfig['flavor-name'] == flavor.name:
                    compute_info['flavor_id'] = flavor.id
                if self.uconfig['flavor-alt-name'] == flavor.name:
                    compute_info['flavor_alt_id'] = flavor.id
        except:
            log("Nova does not appear to be ready, deferring nova query")
        return compute_info

    @property
    def creds(self):
        return self.relation.credentials()

    @property
    def auth_url(self):
        bob = self.get_keystone_client() or 'bugger'
        return bob

    def get_present_services(self):
        self.init_keystone_client()
        print(self.ks.services.list())
        services = [svc.name for svc in self.ks.services.list() if svc.enabled]
#        if DashboardRelation().get('dashboard_url'):
#            services.append('horizon')
        print(services)
        return services

    @property
    def service_info(self):
        services = {}
        tempest_candidates = ['ceilometer', 'cinder', 'glance', 'heat',
                              'horizon', 'ironic', 'neutron', 'nova',
                              'sahara', 'swift', 'trove', 'zaqar', 'neutron']
        print("1")
        present_svcs = self.get_present_services()
        print("2")
        # If not running in an action context asssume auto mode
        try:
            action_args = action_get()
        except:
            action_args = {'service-whitelist': 'auto'}

        if action_args['service-whitelist'] == 'auto':
            white_list = []
            for svc in present_svcs:
                if svc in tempest_candidates:
                    white_list.append(svc)
        else:
            white_list = action_args['service-whitelist']
        for svc in tempest_candidates:
            if svc in white_list:
                services[svc] = 'true'
            else:
                services[svc] = 'false'



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

