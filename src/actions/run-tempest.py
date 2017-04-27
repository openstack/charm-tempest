#!/usr/bin/env python3
import sys
sys.path.append('lib')

import charm.openstack.tempest as tempest
import charms.reactive as reactive
import charms.reactive.bus as bus
import charmhelpers.core.hookenv as hookenv

# Make sure that reactive is bootstrapped and all the states are setup
# properly
from charms.layer import basic
basic.bootstrap_charm_deps()
basic.init_config_states()

if __name__ == '__main__':
    # charms.reactive 0.4.6 moved the auto discovery of interfaces out of the
    # module load and into the main() function.  Actions don't want to run the
    # main (as we don't want the handlers/hooks to run) so this just finds the
    # interfaces to the '.from_state()' function will get the interface object.
    bus.discover()
    identity_int = reactive.RelationBase.from_state('identity-admin.available')
    if identity_int is None:
        # The interface isn't connected, so we can't do this yet
        hookenv.action_fail(
            "The identity-admin interface is not available - bailing")
    else:
        tempest.render_configs([identity_int])
        tempest.run_test('smoke')
