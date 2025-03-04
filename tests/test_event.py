import unittest
import os

from electrum_aionostr.event import Event
from electrum_aionostr.key import PrivateKey

class TestEvent(unittest.TestCase):

    def test_verify(self):
        privkey1 = PrivateKey(os.urandom(32))
        privkey2 = PrivateKey(os.urandom(32))

        event = Event(
            pubkey=privkey1.public_key.hex(),
            content="test"
        )
        # verify event without signature
        self.assertFalse(event.verify())
        # verify event with correct signature
        event.sign(privkey1.hex())
        self.assertTrue(event.verify())
        # verify event with incorrect signature
        event.sign(privkey2.hex())
        self.assertFalse(event.verify())
