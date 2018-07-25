# CDDL fragment MACed Message with Recipients
#
# COSE_Mac = [
#       Headers,
#       payload : bstr / nil,
#       tag : bstr,
#       recipients :[+COSE_recipient]
# ]
#


import binascii
import copy

import cbor

from pycose import cosemessage, maccommon
from pycose.attributes import CoseAttrs


@cosemessage.CoseMessage.record_cbor_tag(97)
class MacMessage(maccommon.MacCommon):
    context = "MAC"
    cbor_tag = 97

    def __init__(self, p_header=CoseAttrs(), u_header=CoseAttrs(), payload=None, key=None, recipients=CoseAttrs()):
        super(MacMessage, self).__init__(
            copy.deepcopy(p_header),
            copy.deepcopy(u_header),
            payload
        )
        self._key = key
        self._recipients = self._convert_to_coseattrs(copy.deepcopy(recipients))

    @property
    def key(self):
        return self._key

    @key.setter
    def key(self, new_value):
        if isinstance(new_value, bytes):
            self._key = new_value
        else:
            raise ValueError("Key must be of type bytes")

    def encode(self):
        """Encodes the message into a CBOR array"""

        if len(binascii.hexlify(self.auth_tag)) not in [16, 32, 64, 96, 128]:
            raise ValueError("Tag has invalid size.")

        return cbor.dumps(cbor.Tag(self.cbor_tag, [self.encoded_protected_header, self.unprotected_header,
                                                   self.payload, self.auth_tag, self.recipients]))

    @property
    def recipients(self):
        correct_recpt_format = []
        for key in self._recipients:
            correct_recpt_format.append(copy.deepcopy(self._recipients[key]))

        for rcpt in correct_recpt_format:
            # encode protected attributes 'comme il faut'
            if not rcpt[0]:
                rcpt[0] = bytes()
            else:
                rcpt[0] = cbor.dumps(rcpt[0])

        return correct_recpt_format

    @recipients.setter
    def recipients(self, new_value):
        new_value = copy.deepcopy(new_value)
        if isinstance(new_value, dict) or isinstance(new_value, CoseAttrs):
            if new_value is not None and len(new_value) != 0:

                self._recipients = CoseAttrs()
                key = 1
                for rcpt in new_value:
                    self._recipients[key] = rcpt
                    key += 1

                # cbor decode the byte string protected header, so that we can do lookups

                for rcpt in self._recipients:
                    if len(self._recipients[rcpt][0]) != 0:
                        protected_recipient = CoseAttrs()
                        new_value = cbor.loads(self._recipients[rcpt][0])
                        for key, value in new_value.items():
                            protected_recipient[key] = value

                        self._recipients[rcpt][0] = copy.deepcopy(protected_recipient)
                    else:
                        self._recipients[rcpt][0] = CoseAttrs()

                for rcpt in self._recipients:
                    if len(self._recipients[rcpt][1]) != 0:
                        unprotected_recipient = CoseAttrs()
                        for key, value in self._recipients[rcpt][1].items():
                            unprotected_recipient[key] = value

                        self._recipients[rcpt][1] = copy.deepcopy(unprotected_recipient)
                    else:
                        self._recipients[rcpt][1] = CoseAttrs()
            else:
                self._recipients = CoseAttrs()

    def add_to_recipients(self, recpt, label, value, where):
        if recpt in self._recipients:
            if where == "PROTECTED":
                self._recipients[recpt][0][label] = value

            if where == "UNPROTECTED":
                self._recipients[recpt][1][label] = value
        else:
            # make new recipient
            recipient = [CoseAttrs(), CoseAttrs(), b'']
            # add the attribute
            if where == "PROTECTED":
                recipient[0][label] = value

            if where == "UNPROTECTED":
                recipient[1][label] = value

            self._recipients[recpt] = recipient

    def find_in_recipients(self, label):
        found = None
        for rcpt in self._recipients:
            if label in self._recipients[rcpt][0]:
                found = self._recipients[rcpt][0][label]

            if label in self._recipients[rcpt][1]:
                found = self._recipients[rcpt][1][label]

        return found