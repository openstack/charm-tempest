import unittest


class TestNoOp(unittest.TestCase):
    """Placeholder - Write Me!"""
    # XXX (beisner): with the charm.openstack vs lib/charm/openstack/tempest
    # module namespace collision, and with the hard requirement to have some
    # sort of unit test passing, here is a temporary inert noop test.  After
    # charms_openstack module is completed, and this tempest charm is
    # refactored to use it, revisit this and add actual unit tests.
    def test_noop(self):
        """Test Nothing"""
        pass
