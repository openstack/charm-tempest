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

import mock
import sys

sys.path.append('src')
sys.path.append('src/lib')

# Mock out charmhelpers so that we can test without it.
import charms_openstack.test_mocks  # noqa
charms_openstack.test_mocks.mock_charmhelpers()


# Mock out OpenStack clients the tempest charm imports so they are not
# required for testing.
glanceclient = mock.MagicMock()
sys.modules['glanceclient'] = glanceclient

keystoneauth1 = mock.MagicMock()
sys.modules['keystoneauth1'] = keystoneauth1
sys.modules['keystoneauth1.identity'] = keystoneauth1.identity
sys.modules['keystoneauth1.identity.v1'] = keystoneauth1.identity.v1
sys.modules['keystoneauth1.identity.v2'] = keystoneauth1.identity.v2
sys.modules['keystoneauth1.session'] = keystoneauth1.session

keystoneclient = mock.MagicMock()
sys.modules['keystoneclient'] = keystoneclient
sys.modules['keystoneclient.auth'] = keystoneclient.auth
sys.modules['keystoneclient.auth.identity'] = keystoneclient.auth.identity
sys.modules['keystoneclient.auth.identity.v3'] = (
    keystoneclient.auth.identity.v3)
sys.modules['keystoneclient.v2_0'] = keystoneclient.v2_0
sys.modules['keystoneclient.v2_0.client'] = keystoneclient.v2_0.client
sys.modules['keystoneclient.v3'] = keystoneclient.v3
sys.modules['keystoneclient.v3.client'] = keystoneclient.v3.client
sys.modules['keystoneclient.session'] = keystoneclient.session

neutronclient = mock.MagicMock()
sys.modules['neutronclient'] = neutronclient
sys.modules['neutronclient.v2_0'] = neutronclient.v2_0
sys.modules['neutronclient.v2_0.client'] = neutronclient.v2_0.client

novaclient = mock.MagicMock()
sys.modules['novaclient'] = novaclient
sys.modules['novaclient.client'] = novaclient.client
