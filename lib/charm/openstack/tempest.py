import glanceclient
import keystoneclient.v2_0 as keystoneclient
import neutronclient.v2_0.client as neutronclient
import novaclient.v2 as novaclient
import urllib

import charm.openstack.charm as charm
import charm.openstack.adapters as adapters
import charmhelpers.core.hookenv as hookenv

tempest_charm = None


def get_charm():
    """ Return a new instance of TempestCharm or existing global instance
    @returns TempestCharm
    """
    global tempest_charm
    if tempest_charm is None:
        tempest_charm = TempestCharmFactory.charm()
    return tempest_charm


class TempestAdminAdapter(adapters.OpenStackRelationAdapter):

    """Inspect relations and provide properties that can be used when
       rendering templates"""

    interface_type = "identity-admin"

    def __init__(self, relation):
        """Initialise a keystone client and collect user defined config"""
        self.kc = None
        super(TempestAdminAdapter, self).__init__(relation)
        self.init_keystone_client()
        self.uconfig = hookenv.config()

    @property
    def keystone_info(self):
        """Collection keystone information from keystone relation"""
        return self.relation.credentials()

    def init_keystone_client(self):
        """Initialise keystone client"""
        if self.kc:
            return
        self.keystone_auth_url = '{}://{}:{}/v2.0'.format(
            'http',
            self.keystone_info['service_hostname'],
            self.keystone_info['service_port']
        )
        auth = {
            'username': self.keystone_info['service_username'],
            'password': self.keystone_info['service_password'],
            'auth_url': self.keystone_auth_url,
            'tenant_name': self.keystone_info['service_tenant_name'],
            'region_name': self.keystone_info['service_region'],
        }
        try:
            self.kc = keystoneclient.client.Client(**auth)
        except:
            hookenv.log("Keystone is not ready, deferring keystone query")

    @property
    def ec2_creds(self):
        """Generate EC2 style tokens or return existing EC2 tokens

        @returns {'access_token' token1, 'secret_token': token2}
        """
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
        """Return image ids for the user-defined image names

        @returns {'image_id' id1, 'image_alt_id': id2}
        """
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
            hookenv.log("Glance is not ready, deferring glance query")
        return image_info

    @property
    def network_info(self):
        """Return public network and router ids for user-defined router and
           network names

        @returns {'image_id' id1, 'image_alt_id': id2}
        """
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
                hookenv.log("Router not found")
            else:
                router = routers['routers'][0]
                network_info['router_id'] = router['id']
            networks = neutron_client.list_networks(
                name=self.uconfig['network-name'])
            if len(networks['networks']) == 0:
                hookenv.log("network not found")
            else:
                network = networks['networks'][0]
                network_info['public_network_id'] = network['id']
        except:
            hookenv.log("Neutron is not ready, deferring neutron query")
        return network_info

    @property
    def compute_info(self):
        """Return flavor ids for user-defined flavors

        @returns {'flavor_id' id1, 'flavor_alt_id': id2}
        """
        self.init_keystone_client()
        nova_ep = self.kc.service_catalog.url_for(
            service_type='compute',
            endpoint_type='publicURL'
        )
        compute_info = {}
        compute_info['nova_endpoint'] = nova_ep
        url = urllib.parse.urlparse(nova_ep)
        compute_info['nova_base'] = '{}://{}'.format(url.scheme,
                                                     url.netloc.split(':')[0])
        try:
            nova_client = novaclient.client.Client(
                self.keystone_info['service_username'],
                self.keystone_info['service_password'],
                self.keystone_info['service_tenant_name'],
                self.keystone_auth_url,
            )
            for flavor in nova_client.flavors.list():
                if self.uconfig['flavor-name'] == flavor.name:
                    compute_info['flavor_id'] = flavor.id
                if self.uconfig['flavor-alt-name'] == flavor.name:
                    compute_info['flavor_alt_id'] = flavor.id
        except:
            hookenv.log("Nova is not ready, deferring nova query")
        return compute_info


    def get_present_services(self):
        """Query keystone catalogue for a list for registered services

        @returns [svc1, svc2, ...]: List of registered services
        """
        self.init_keystone_client()
        services = [svc.name for svc in self.kc.services.list() if svc.enabled]
        return services

    @property
    def service_info(self):
        """Assemble a list of services tempest should tests

        Compare the list of keystone registered services with the services the
        user has requested be tested. If in 'auto' mode test all services
        registered in keystone.
        
        @returns [svc1, svc2, ...]: List of services to test
        """
        service_info = {}
        tempest_candidates = ['ceilometer', 'cinder', 'glance', 'heat',
                              'horizon', 'ironic', 'neutron', 'nova',
                              'sahara', 'swift', 'trove', 'zaqar', 'neutron']
        present_svcs = self.get_present_services()
        # If not running in an action context asssume auto mode
        try:
            action_args = hookenv.action_get()
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
                service_info[svc] = 'true'
            else:
                service_info[svc] = 'false'
        return service_info


class TempestAdapters(adapters.OpenStackRelationAdapters):
    """
    Adapters class for the Tempest charm.
    """
    relation_adapters = {
        'identity_admin': TempestAdminAdapter,
    }

    def __init__(self, relations):
        super(TempestAdapters, self).__init__(
            relations,
            options=TempestConfigurationAdapter)


class TempestConfigurationAdapter(adapters.ConfigurationAdapter):
    """
    Manipulate user supplied config as needed
    """
    def __init__(self):
        super(TempestConfigurationAdapter, self).__init__()


class TempestCharm(charm.OpenStackCharm):

    """Directories and files used for running tempest"""
    TEMPEST_ROOT = '/var/lib/tempest/'
    TEMPEST_LOGDIR = TEMPEST_ROOT + '/logs'
    TEMPEST_CONF = TEMPEST_ROOT + '/tempest.conf'
    """pip.conf for proxy settings etc"""
    PIP_CONF = '/root/.pip/pip.conf'

    """List of packages charm should install
       XXX The install hook is currently installing most packages ahead of
           this because modules like keystoneclient are needed at load time
    """
    packages = [
        'git', 'testrepository', 'subunit', 'python-nose', 'python-lxml',
        'python-boto', 'python-junitxml', 'python-subunit',
        'python-testresources', 'python-oslotest', 'python-stevedore',
        'python-cinderclient', 'python-glanceclient', 'python-heatclient',
        'python-keystoneclient', 'python-neutronclient', 'python-novaclient',
        'python-swiftclient', 'python-ceilometerclient', 'openvswitch-test',
        'python3-cinderclient', 'python3-glanceclient', 'python3-heatclient',
        'python3-keystoneclient', 'python3-neutronclient',
        'python3-novaclient', 'python3-swiftclient',
        'python3-ceilometerclient', 'openvswitch-common', 'libffi-dev',
        'libssl-dev', 'python-dev', 'python-cffi'
    ]

    """Use the Tempest specific adapters"""
    adapters_class = TempestAdapters
    """Tempest has no running services so no services need restarting on
       config file change
    """
    restart_map = {
        TEMPEST_CONF: [],
        PIP_CONF: [],
    }


class TempestCharmFactory(charm.OpenStackCharmFactory):

    releases = {
        'liberty': TempestCharm
    }

    first_release = 'liberty'
