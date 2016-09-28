#!/usr/bin/env python3
import sys
sys.path.append('lib')

import charm.openstack.tempest as tempest
import charms.reactive as reactive


if __name__ == '__main__':
    # Cloud may have different artifacts (flavors, images etc) since last run
    # so rerun handlers file to regenerate config.
    reactive.main()
    tempest.run_test('smoke')
