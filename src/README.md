# Overview

> **WARNING**: DO NOT USE OR CONTRIBUTE.
> [THIS CHARM IS DEPRECATED](https://docs.openstack.org/charm-guide/latest/openstack-charms.html).

This charm exists to provide an example integration of Tempest, for the purpose
of test and reference.  It is not intended for production use in any case.

Tempest is a set of integration tests to be run against a live OpenStack
cluster. Tempest has batteries of tests for OpenStack API validation,
Scenarios, and other specific tests useful in validating an OpenStack
deployment.

The Tempest Charm can be deployed into a new or existing Juju model containing
an OpenStack deployment to execute sets or subsets of Tempest tests.

# Usage

NOTICE: At this time, the Tempest charm is in development and is in a
proof-of-concept alpha state.

Development and related discussion occurs on the Freenode #openstack-charms IRC
channel.

TLDR:  Deploy the built charm and relate it to keystone and openstack-dashboard.
See config.yaml as annotated.

More docs to come as this matures.

Executing the run-tempest action:

juju run-action tempest/0 run-tempest --wait

# Contact Information

See the [OpenStack Charm Guide](http://docs.openstack.org/developer/charm-guide/)
or discuss on Freenode IRC: #openstack-charms
