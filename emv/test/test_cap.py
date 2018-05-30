from unittest2 import TestCase
from emv.protocol.response import RAPDU
from emv.protocol.structures import TLV
from emv.util import unformat_bytes
from emv.cap import get_cap_value, get_arqc_req

from emv.test.fixtures import APP_DATA


class TestCAP(TestCase):

    def test_arqc_req(self):
        # Comparing with a valid test request from barclays_pinsentry.c
        req = get_arqc_req(TLV.unmarshal(APP_DATA)[0x70])
        data = unformat_bytes('''80 AE 80 00 1D 00 00 00 00 00 00 00 00 00 00 00 00 00 00 80 00
                                 00 00 00 00 00 01 01 01 00 00 00 00 00 00''')
        self.assertEqual(req.marshal(), data)

    def test_arqc_req_payment(self):
        # Payment of £1234.56, account number of 78901234
        req = get_arqc_req(TLV.unmarshal(APP_DATA)[0x70], value=1234.56, challenge=78901234)
        data = unformat_bytes('''80 AE 80 00 1D 00 00 00 12 34 56 00 00 00 00 00 00 00 00 80 00
                                 00 00 00 00 00 01 01 01 00 78 90 12 34 00''')
        self.assertEqual(req.marshal(), data)

        # Payment of £15.00, account number of 78901234
        req = get_arqc_req(TLV.unmarshal(APP_DATA)[0x70], value=15.00, challenge=78901234)
        data = unformat_bytes('''80 AE 80 00 1D 00 00 00 00 15 00 00 00 00 00 00 00 00 00 80 00
                                 00 00 00 00 00 01 01 01 00 78 90 12 34 00''')
        self.assertEqual(req.marshal(), data)

    def test_arqc_req_challenge(self):
        # Challenge of 78901234
        req = get_arqc_req(TLV.unmarshal(APP_DATA)[0x70], challenge=78901234)
        data = unformat_bytes('''80 AE 80 00 1D 00 00 00 00 00 00 00 00 00 00 00 00 00 00 80 00
                                 00 00 00 00 00 01 01 01 00 78 90 12 34 00''')
        self.assertEqual(req.marshal(), data)

    def test_pinsentry_equivalence(self):
        # Real response from barclays-pinsentry.c, with its calculated response
        data = unformat_bytes('80 12 80 09 5F 0F 9D 37 98 E9 3F 12 9A 06 0A 0A 03 A4 90 00 90 00')
        res = RAPDU.unmarshal(data)
        self.assertEqual(get_cap_value(res), 46076570)
