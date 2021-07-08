# Overview

> **WARNING**: DO NOT USE OR CONTRIBUTE.
> [THIS CHARM IS DEPRECATED](https://docs.openstack.org/charm-guide/latest/openstack-charms.html).

This is a "source" charm, which is intended to be strictly the top
layer of a built charm.  This structure declares that any included
layer assets are not intended to be consumed as a layer from a
functional or design standpoint.

# Test and Build

```
tox -e pep8
tox -e py34  # or py27 or py35
tox -e build
```

# Contact Information

OFTC IRC: #openstack-charms
