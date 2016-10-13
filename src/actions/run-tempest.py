#!/usr/bin/env python3
import sys
sys.path.append('lib')

import charm.openstack.tempest as tempest
import charms.reactive as reactive


if __name__ == '__main__':
    identity_int = reactive.RelationBase.from_state('identity-admin.available')
    tempest.render_configs([identity_int])
    tempest.run_test('smoke')
