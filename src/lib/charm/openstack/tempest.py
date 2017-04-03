import os
import re
import subprocess
import time
import urllib

import glanceclient
import keystoneauth1
import keystoneauth1.identity.v2 as keystoneauth1_v2
import keystoneauth1.session as keystoneauth1_session
import keystoneclient.v2_0.client as keystoneclient_v2
import keystoneclient.v3.client as keystoneclient_v3
import keystoneclient.auth.identity.v3 as keystone_id_v3
import keystoneclient.session as session
import neutronclient.v2_0.client as neutronclient
import novaclient.client as novaclient_client

import charms_openstack.charm as charm
import charms_openstack.adapters as adapters
import charmhelpers.core.hookenv as hookenv
import charmhelpers.core.host as host
import charmhelpers.fetch as fetch


def install():
    """Use the singleton from the TempestCharm to install the packages on the
    unit
    """
    TempestCharm.singleton.install()


def render_configs(interfaces_list):
    """Using a list of interfaces, render the configs and, if they have
    changes, restart the services on the unit.
    """
    if not os.path.isdir(TempestCharm.TEMPEST_LOGDIR):
        os.makedirs(TempestCharm.TEMPEST_LOGDIR)
    TempestCharm.singleton.render_with_interfaces(interfaces_list)
    TempestCharm.singleton.assess_status()


def run_test(tox_target):
    """Use the singleton from the TempestCharm to install the packages on the
    unit
    """
    TempestCharm.singleton.run_test(tox_target)


def assess_status():
    """Use the singleton from the TempestCharm to install the packages on the
    unit
    """
    TempestCharm.singleton.assess_status()


class TempestAdminAdapter(adapters.OpenStackRelationAdapter):

    """Inspect relations and provide properties that can be used when
       rendering templates"""

    interface_type = "identity-admin"

    def __init__(self, relation):
        """Initialise a keystone client and collect user defined config"""
        self.kc = None
        self.keystone_session = None
        self.api_version = '2'
        super(TempestAdminAdapter, self).__init__(relation)
        self.init_keystone_client()
        self.uconfig = hookenv.config()

    @property
    def keystone_info(self):
        """Collection keystone information from keystone relation"""
        ks_info = self.relation.credentials()
        ks_info['default_credentials_domain_name'] = 'default'
        if ks_info.get('api_version'):
            ks_info['api_version'] = ks_info.get('api_version')
        else:
            ks_info['api_version'] = self.api_version
        if not ks_info.get('service_user_domain_name'):
            ks_info['service_user_domain_name'] = 'admin_domain'

        return ks_info

    @property
    def ks_client(self):
        if not self.kc:
            self.init_keystone_client()
        return self.kc

    def keystone_auth_url(self, api_version=None):
        if not api_version:
            api_version = self.keystone_info.get('api_version', '2')
        ep_suffix = {
            '2': 'v2.0',
            '3': 'v3'}[api_version]
        return '{}://{}:{}/{}'.format(
            'http',
            self.keystone_info['service_hostname'],
            self.keystone_info['service_port'],
            ep_suffix,
        )

    def resolve_endpoint(self, service_type, interface):
        if self.api_version == '2':
            ep = self.ks_client.service_catalog.url_for(
                service_type=service_type,
                endpoint_type='{}URL'.format(interface)
            )
        else:
            svc_id = self.ks_client.services.find(type=service_type).id
            ep = self.ks_client.endpoints.find(
                service_id=svc_id,
                interface=interface).url
        return ep

    def set_keystone_v2_client(self):
        self.keystone_session = None
        self.kc = keystoneclient_v2.Client(**self.admin_creds_v2)

    def set_keystone_v3_client(self):
        auth = keystone_id_v3.Password(**self.admin_creds_v3)
        self.keystone_session = session.Session(auth=auth)
        self.kc = keystoneclient_v3.Client(session=self.keystone_session)

    def init_keystone_client(self):
        """Initialise keystone client"""
        if self.kc:
            return
        if self.keystone_info.get('api_version', '2') > '2':
            self.set_keystone_v3_client()
            self.api_version = '3'
        else:
            # XXX Temporarily catching the Unauthorized exception to deal with
            # the case (pre-17.02) where the keystone charm maybe in v3 mode
            # without telling charms via the identity-admin relation
            try:
                self.set_keystone_v2_client()
                self.api_version = '2'
            except keystoneauth1.exceptions.http.Unauthorized:
                self.set_keystone_v3_client()
                self.api_version = '3'
        self.kc.services.list()

    def admin_creds_base(self, api_version):
        return {
            'username': self.keystone_info['service_username'],
            'password': self.keystone_info['service_password'],
            'auth_url': self.keystone_auth_url(api_version=api_version)}

    @property
    def admin_creds_v2(self):
            creds = self.admin_creds_base(api_version='2')
            creds['tenant_name'] = self.keystone_info['service_tenant_name']
            creds['region_name'] = self.keystone_info['service_region']
            return creds

    @property
    def admin_creds_v3(self):
            creds = self.admin_creds_base(api_version='3')
            creds['project_name'] = self.keystone_info.get(
                'service_project_name',
                'admin')
            creds['user_domain_name'] = self.keystone_info.get(
                'service_user_domain_name',
                'admin_domain')
            creds['project_domain_name'] = self.keystone_info.get(
                'service_project_domain_name',
                'Default')
            return creds

    @property
    def ec2_creds(self):
        """Generate EC2 style tokens or return existing EC2 tokens

        @returns {'access_token' token1, 'secret_token': token2}
        """
        _ec2creds = {}
        if self.api_version == '2':
            current_creds = self.ks_client.ec2.list(self.ks_client.user_id)
            if current_creds:
                _ec2creds = current_creds[0]
            else:
                creds = self.ks_client.ec2.create(
                    self.ks_client.user_id,
                    self.ks_client.tenant_id)
                _ec2creds = {
                    'access_token': creds.access,
                    'secret_token': creds.secret}
        return _ec2creds

    @property
    def image_info(self):
        """Return image ids for the user-defined image names

        @returns {'image_id' id1, 'image_alt_id': id2}
        """
        image_info = {}
        if self.service_present('glance'):
            if self.keystone_session:
                glance_client = glanceclient.Client(
                    '2', session=self.keystone_session)
            else:
                glance_ep = self.resolve_endpoint('image', 'public')
                glance_client = glanceclient.Client(
                    '2', glance_ep, token=self.ks_client.auth_token)
            for image in glance_client.images.list():
                if self.uconfig.get('glance-image-name') == image.name:
                    image_info['image_id'] = image.id
                if self.uconfig.get('image-ssh-user'):
                    image_info['image_ssh_user'] = \
                        self.uconfig.get('image-ssh-user')
                if self.uconfig.get('glance-alt-image-name') == image.name:
                    image_info['image_alt_id'] = image.id
                if self.uconfig.get('image-alt-ssh-user'):
                    image_info['image_alt_ssh_user'] = \
                        self.uconfig.get('image-alt-ssh-user')
        return image_info

    @property
    def network_info(self):
        """Return public network and router ids for user-defined router and
           network names

        @returns {'public_network_id' id1, 'router_id': id2}
        """
        network_info = {}
        if self.service_present('neutron'):
            if self.keystone_session:
                neutron_client = neutronclient.Client(
                    session=self.keystone_session)
            else:
                neutron_ep = self.ks_client.service_catalog.url_for(
                    service_type='network',
                    endpoint_type='publicURL')
                neutron_client = neutronclient.Client(
                    endpoint_url=neutron_ep,
                    token=self.ks_client.auth_token)
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
            networks = neutron_client.list_networks(
                name=self.uconfig['floating-network-name'])
            if len(networks['networks']) == 0:
                hookenv.log("Floating network name not found")
            else:
                network_info['floating_network_name'] = \
                    self.uconfig['floating-network-name']
        return network_info

    def service_present(self, service):
        """Check if a given service type is registered in the catalogue

        :params service: string Service type
        @returns Boolean: True if service is registered
        """
        return service in self.get_present_services()

    def get_nova_client(self):
        if not self.keystone_session:
            auth = keystoneauth1_v2.Password(
                auth_url=self.keystone_auth_url(),
                username=self.keystone_info['service_username'],
                password=self.keystone_info['service_password'],
                tenant_name=self.keystone_info['service_tenant_name'])
            self.keystone_session = keystoneauth1_session.Session(auth=auth)
        return novaclient_client.Client(
            2, session=self.keystone_session)

    @property
    def compute_info(self):
        """Return flavor ids for user-defined flavors

        @returns {'flavor_id' id1, 'flavor_alt_id': id2}
        """
        compute_info = {}
        if self.service_present('nova'):
            nova_client = self.get_nova_client()
            nova_ep = self.resolve_endpoint('compute', 'public')
            url = urllib.parse.urlparse(nova_ep)
            compute_info['nova_base'] = '{}://{}'.format(
                url.scheme,
                url.netloc.split(':')[0])
            for flavor in nova_client.flavors.list():
                if self.uconfig['flavor-name'] == flavor.name:
                    compute_info['flavor_id'] = flavor.id
                if self.uconfig['flavor-alt-name'] == flavor.name:
                    compute_info['flavor_alt_id'] = flavor.id
        return compute_info

    def get_present_services(self):
        """Query keystone catalogue for a list for registered services

        @returns [svc1, svc2, ...]: List of registered services
        """
        services = [svc.name
                    for svc in self.ks_client.services.list()
                    if svc.enabled]
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

    release = 'liberty'
    name = 'tempest'

    required_relations = ['identity-admin']
    """Directories and files used for running tempest"""
    TEMPEST_ROOT = '/var/lib/tempest'
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

    @property
    def all_packages(self):
        _packages = self.packages[:]
        if host.lsb_release()['DISTRIB_RELEASE'] > '14.04':
            _packages.append('tox')
        else:
            _packages.append('python-tox')
        return _packages

    def setup_directories(self):
        for tempest_dir in [self.TEMPEST_ROOT, self.TEMPEST_LOGDIR]:
            if not os.path.exists(tempest_dir):
                os.mkdir(tempest_dir)

    def setup_git(self, branch, git_dir):
        """Clone tempest and symlink in rendered tempest.conf"""
        conf = hookenv.config()
        if not os.path.exists(git_dir):
            git_url = conf['tempest-source']
            fetch.install_remote(str(git_url), dest=str(git_dir),
                                 branch=str(branch), depth=str(1))
        conf_symlink = git_dir + '/tempest/etc/tempest.conf'
        if not os.path.exists(conf_symlink):
            os.symlink(self.TEMPEST_CONF, conf_symlink)

    def execute_tox(self, run_dir, logfile, tox_target):
        """Trigger tempest run through tox setting proxies if needed"""
        env = os.environ.copy()
        conf = hookenv.config()
        if conf.get('http-proxy'):
            env['http_proxy'] = conf['http-proxy']
        if conf.get('https-proxy'):
            env['https_proxy'] = conf['https-proxy']
        cmd = ['tox', '-e', tox_target]
        f = open(logfile, "w")
        subprocess.call(cmd, cwd=run_dir, stdout=f, stderr=f, env=env)

    def get_tempest_files(self, branch_name):
        """Prepare tempest files and directories

        @return git_dir, logfile, run_dir
        """
        log_time_str = time.strftime("%Y%m%d%H%M%S", time.gmtime())
        git_dir = '{}/tempest-{}'.format(self.TEMPEST_ROOT, branch_name)
        logfile = '{}/run_{}.log'.format(self.TEMPEST_LOGDIR, log_time_str)
        run_dir = '{}/tempest'.format(git_dir)
        return git_dir, logfile, run_dir

    def parse_tempest_log(self, logfile):
        """Read tempest logfile and return summary as dict

        @return dict: Dictonary of summary data
        """
        summary = {}
        with open(logfile, 'r') as tempest_log:
            summary_line = False
            for line in tempest_log:
                if line.strip() == "Totals":
                    summary_line = True
                if line.strip() == "Worker Balance":
                    summary_line = False
                if summary_line:
                    # Match lines like: ' - Unexpected Success: 0'
                    matchObj = re.match(
                        r'(.*)- (.*?):\s+(.*)', line, re.M | re.I)
                    if matchObj:
                        key = matchObj.group(2)
                        key = key.replace(' ', '-').replace(':', '').lower()
                        summary[key] = matchObj.group(3)
        return summary

    def run_test(self, tox_target):
        """Run smoke tests"""
        action_args = hookenv.action_get()
        branch_name = action_args['branch']
        git_dir, logfile, run_dir = self.get_tempest_files(branch_name)
        self.setup_directories()
        self.setup_git(branch_name, git_dir)
        self.execute_tox(run_dir, logfile, tox_target)
        action_info = self.parse_tempest_log(logfile)
        action_info['tempest-logfile'] = logfile
        hookenv.action_set(action_info)
