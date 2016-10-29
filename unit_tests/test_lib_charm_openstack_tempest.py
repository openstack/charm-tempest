# Copyright 2016 Canonical Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
from __future__ import print_function

import io
import mock

import charms_openstack.test_utils as test_utils
import charm.openstack.tempest as tempest
import unit_tests.tempest_output


class Helper(test_utils.PatchHelper):

    def setUp(self):
        super().setUp()
        self.patch_release(tempest.TempestCharm.release)


class TestTempestAdminAdapter(test_utils.PatchHelper):

    def test_init(self):
        self.patch_object(tempest.hookenv, 'config')
        self.patch_object(tempest.TempestAdminAdapter, 'init_keystone_client')
        self.patch_object(
            tempest.adapters.OpenStackRelationAdapter, '__init__')
        tempest.TempestAdminAdapter('rel2')
        self.init_keystone_client.assert_called_once_with()
        self.__init__.assert_called_once_with('rel2')

    def test_init_keystone_client(self):
        ks_info = {
            'service_hostname': 'kshost',
            'service_port': '5001',
            'service_username': 'user1',
            'service_password': 'pass1',
            'service_tenant_name': 'svc',
            'service_region': 'reg1'}
        self.patch_object(tempest.keystoneclient.client, 'Client')
        self.patch_object(tempest.hookenv, 'config')
        self.patch_object(
            tempest.adapters.OpenStackRelationAdapter, '__init__')
        self.patch_object(
            tempest.TempestAdminAdapter,
            'keystone_info',
            new=ks_info)
        a = tempest.TempestAdminAdapter('rel2')
        a.init_keystone_client()
        self.Client.assert_called_once_with(
            auth_url='http://kshost:5001/v2.0',
            password='pass1',
            region_name='reg1',
            tenant_name='svc',
            username='user1')

    def test_ec2_creds(self):
        self.patch_object(tempest.hookenv, 'config')
        self.patch_object(tempest.TempestAdminAdapter, 'init_keystone_client')
        self.patch_object(
            tempest.adapters.OpenStackRelationAdapter, '__init__')
        kc = mock.MagicMock()
        creds = mock.MagicMock()
        creds.access = 'ac2'
        creds.secret = 'st2'
        kc.user_id = 'bob'
        kc.ec2.list = lambda x: [creds]
        self.patch_object(tempest.TempestAdminAdapter, 'ks_client', new=kc)
        a = tempest.TempestAdminAdapter('rel2')
        self.assertEqual(a.ec2_creds, {'access_token': 'ac2',
                                       'secret_token': 'st2'})

    def test_image_info(self):
        self.patch_object(tempest.hookenv, 'config')
        self.patch_object(tempest.TempestAdminAdapter, 'init_keystone_client')
        self.patch_object(
            tempest.adapters.OpenStackRelationAdapter, '__init__')
        self.patch_object(tempest.TempestAdminAdapter, 'ks_client')
        self.patch_object(tempest.glanceclient, 'Client')
        self.config.return_value = {
            'glance-image-name': 'img1',
            'glance-alt-image-name': 'altimg',
        }
        kc = mock.MagicMock()
        kc.service_catalog.url_for = \
            lambda service_type=None, endpoint_type=None: 'http://glance'
        self.ks_client.return_value = kc
        img1 = mock.MagicMock()
        img1.name = 'img1'
        img1.id = 'img1_id'
        img2 = mock.MagicMock()
        img2.name = 'img2'
        img2.id = 'img2_id'
        gc = mock.MagicMock()
        gc.images.list = lambda: [img1, img2]
        self.Client.return_value = gc
        a = tempest.TempestAdminAdapter('rel2')
        self.assertEqual(a.image_info, {'image_id': 'img1_id'})

    def test_network_info(self):
        self.patch_object(tempest.hookenv, 'config')
        self.patch_object(tempest.TempestAdminAdapter, 'init_keystone_client')
        self.patch_object(
            tempest.adapters.OpenStackRelationAdapter, '__init__')
        self.patch_object(tempest.TempestAdminAdapter, 'ks_client')
        self.patch_object(tempest.neutronclient, 'Client')
        router1 = {'id': '16'}
        net1 = {'id': 'pubnet1'}
        kc = mock.MagicMock()
        kc.service_catalog.url_for = \
            lambda service_type=None, endpoint_type=None: 'http://neutron'
        self.ks_client.return_value = kc
        self.config.return_value = {
            'router-name': 'route1',
            'network-name': 'net1'}
        nc = mock.MagicMock()
        nc.list_routers = lambda name=None: {'routers': [router1]}
        nc.list_networks = lambda name=None: {'networks': [net1]}
        self.Client.return_value = nc
        a = tempest.TempestAdminAdapter('rel2')
        self.assertEqual(
            a.network_info,
            {'public_network_id': 'pubnet1', 'router_id': '16'})

    def test_compute_info(self):
        self.patch_object(tempest.hookenv, 'config')
        self.patch_object(tempest.TempestAdminAdapter, 'init_keystone_client')
        self.patch_object(
            tempest.adapters.OpenStackRelationAdapter, '__init__')
        ki = {
            'service_username': 'user',
            'service_password': 'pass',
            'service_tenant_name': 'ten',
        }
        self.patch_object(
            tempest.TempestAdminAdapter,
            'keystone_info',
            new=ki)
        self.patch_object(
            tempest.TempestAdminAdapter,
            'keystone_auth_url',
            new='auth_url')
        self.config.return_value = {
            'flavor-name': 'm3.huuge'}
        kc = mock.MagicMock()
        kc.service_catalog.url_for = \
            lambda service_type=None, endpoint_type=None: 'http://nova:999/bob'
        self.patch_object(tempest.TempestAdminAdapter, 'ks_client', new=kc)
        self.patch_object(tempest.novaclient.client, 'Client')
        _flavor1 = mock.MagicMock()
        _flavor1.name = 'm3.huuge'
        _flavor1.id = 'id1'
        nc = mock.MagicMock()
        nc.flavors.list = lambda: [_flavor1]
        self.Client.return_value = nc
        a = tempest.TempestAdminAdapter('rel2')
        self.assertEqual(
            a.compute_info,
            {
                'flavor_id': 'id1',
                'nova_base': 'http://nova',
                'nova_endpoint': 'http://nova:999/bob'})

    def test_get_present_services(self):
        self.patch_object(tempest.TempestAdminAdapter, 'init_keystone_client')
        self.patch_object(
            tempest.adapters.OpenStackRelationAdapter, '__init__')
        kc = mock.MagicMock()
        svc1 = mock.Mock()
        svc2 = mock.Mock()
        svc3 = mock.Mock()
        svc1.name = 'compute'
        svc1.enabled = True
        svc2.name = 'image'
        svc2.enabled = False
        svc3.name = 'network'
        svc3.enabled = True
        svcs = [svc1, svc2, svc3]
        kc.services.list = lambda: svcs
        self.patch_object(tempest.TempestAdminAdapter, 'ks_client', new=kc)
        a = tempest.TempestAdminAdapter('rel2')
        self.assertEqual(
            a.get_present_services(),
            ['compute', 'network'])

    def test_service_info(self):
        self.patch_object(tempest.TempestAdminAdapter, 'init_keystone_client')
        self.patch_object(
            tempest.adapters.OpenStackRelationAdapter, '__init__')
        self.patch_object(tempest.TempestAdminAdapter, 'get_present_services')
        self.get_present_services.return_value = ['cinder', 'glance']
        self.patch_object(tempest.hookenv, 'action_get')
        self.action_get.return_value = {
            'service-whitelist': 'swift glance'}
        a = tempest.TempestAdminAdapter('rel2')
        self.assertEqual(
            a.service_info,
            {
                'ceilometer': 'false',
                'cinder': 'false',
                'glance': 'true',
                'heat': 'false',
                'horizon': 'false',
                'ironic': 'false',
                'neutron': 'false',
                'nova': 'false',
                'sahara': 'false',
                'swift': 'true',
                'trove': 'false',
                'zaqar': 'false',
                'neutron': 'false'})

    def test_service_info_auto(self):
        self.patch_object(tempest.TempestAdminAdapter, 'init_keystone_client')
        self.patch_object(
            tempest.adapters.OpenStackRelationAdapter, '__init__')
        self.patch_object(tempest.TempestAdminAdapter, 'get_present_services')
        self.get_present_services.return_value = ['cinder', 'glance']
        self.patch_object(tempest.hookenv, 'action_get')
        self.action_get.return_value = {
            'service-whitelist': 'auto'}
        a = tempest.TempestAdminAdapter('rel2')
        self.assertEqual(
            a.service_info,
            {
                'ceilometer': 'false',
                'cinder': 'true',
                'glance': 'true',
                'heat': 'false',
                'horizon': 'false',
                'ironic': 'false',
                'neutron': 'false',
                'nova': 'false',
                'sahara': 'false',
                'swift': 'false',
                'trove': 'false',
                'zaqar': 'false',
                'neutron': 'false'})


class TestTempestCharm(Helper):

    def test_setup_directories(self):
        self.patch_object(tempest.os.path, 'exists')
        self.patch_object(tempest.os, 'mkdir')
        self.exists.return_value = False
        c = tempest.TempestCharm()
        c.setup_directories()
        calls = [
            mock.call('/var/lib/tempest'),
            mock.call('/var/lib/tempest/logs')
        ]
        self.mkdir.assert_has_calls(calls)

    def test_setup_git(self):
        self.patch_object(tempest.hookenv, 'config')
        self.patch_object(tempest.os.path, 'exists')
        self.patch_object(tempest.os, 'symlink')
        self.patch_object(tempest.fetch, 'install_remote')
        self.config.return_value = {'tempest-source': 'git_url'}
        self.exists.return_value = False
        c = tempest.TempestCharm()
        c.setup_git('git_branch', 'git_dir')
        self.install_remote.assert_called_once_with(
            'git_url',
            branch='git_branch',
            depth='1',
            dest='git_dir')
        self.symlink.assert_called_once_with(
            '/var/lib/tempest/tempest.conf',
            'git_dir/tempest/etc/tempest.conf')

    def test_setup_git_noop(self):
        self.patch_object(tempest.hookenv, 'config')
        self.patch_object(tempest.os.path, 'exists')
        self.config.return_value = {'tempest-source': 'git_url'}
        self.patch_object(tempest.os, 'symlink')
        self.patch_object(tempest.fetch, 'install_remote')
        self.exists.return_value = True
        c = tempest.TempestCharm()
        c.setup_git('git_branch', 'git_dir')
        self.assertFalse(self.install_remote.called)
        self.assertFalse(self.symlink.called)

    def test_execute_tox(self):
        # XXX env seems unused
        self.patch_object(tempest.hookenv, 'config')
        self.patch_object(tempest.os.environ, 'copy')
        self.patch_object(tempest.subprocess, 'call')
        os_env = mock.MagicMock()
        self.copy.return_value = os_env
        self.config.return_value = {
            'http-proxy': 'http://proxy',
            'https-proxy': 'https://proxy',
        }
        with mock.patch("builtins.open", return_value="fhandle"):
            c = tempest.TempestCharm()
            c.execute_tox('/tmp/run', '/tmp/t.log', 'py38')
        self.call.assert_called_with(
            ['tox', '-e', 'py38'],
            cwd='/tmp/run',
            stderr='fhandle',
            stdout='fhandle',
            env=os_env)

    def test_get_tempest_files(self):
        self.patch_object(tempest.time, 'strftime')
        self.strftime.return_value = 'teatime'
        c = tempest.TempestCharm()
        self.assertEqual(
            c.get_tempest_files('br1'),
            ('/var/lib/tempest/tempest-br1',
             '/var/lib/tempest/logs/run_teatime.log',
             '/var/lib/tempest/tempest-br1/tempest'))

    def test_parse_tempest_log(self):
        _log_contents = io.StringIO(unit_tests.tempest_output.TEMPEST_OUT)
        expect = {
            'expected-fail': '0',
            'failed': '0',
            'passed': '21',
            'skipped': '41',
            'unexpected-success': '0'}
        with mock.patch("builtins.open", return_value=_log_contents):
            c = tempest.TempestCharm()
            self.assertEqual(c.parse_tempest_log("logfile"), expect)

    def test_run_test(self):
        self.patch_object(tempest.hookenv, 'action_set')
        self.patch_object(tempest.hookenv, 'action_get')
        self.action_get.return_value = {
            'branch': 'br1'}
        self.patch_object(tempest.TempestCharm, 'get_tempest_files')
        self.patch_object(tempest.TempestCharm, 'setup_directories')
        self.patch_object(tempest.TempestCharm, 'setup_git')
        self.patch_object(tempest.TempestCharm, 'execute_tox')
        self.patch_object(tempest.TempestCharm, 'parse_tempest_log')
        self.get_tempest_files.return_value = (
            'git_dir1',
            '/var/log/t.log',
            '/var/tempest/run')
        self.parse_tempest_log.return_value = {'run_info': 'OK'}
        c = tempest.TempestCharm()
        c.run_test('py39')
        self.action_set.assert_called_once_with(
            {'run_info': 'OK', 'tempest-logfile': '/var/log/t.log'})
