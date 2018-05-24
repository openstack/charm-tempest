#!/usr/bin/env python3
import sys
sys.path.append('lib')

# Make sure that reactive is bootstrapped and all the states are setup
# properly
from charms.layer import basic
basic.bootstrap_charm_deps()
basic.init_config_states()

import charm.openstack.tempest as tempest
import charms.reactive.relations as relations
import charmhelpers.core.hookenv as hookenv


if __name__ == '__main__':
    identity_int = relations.endpoint_from_flag('identity-admin.available')
    if identity_int is None:
        # The interface isn't connected, so we can't do this yet
        hookenv.action_fail(
            "The identity-admin interface is not available - bailing")
    else:
        tempest.render_configs([identity_int])
        tempest.run_test('smoke')
