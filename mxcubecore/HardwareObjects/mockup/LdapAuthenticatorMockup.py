from mxcubecore.HardwareObjects.abstract.AbstractAuthenticator import (
    AbstractAuthenticator,
)
from mxcubecore.BaseHardwareObjects import Procedure

"""
<procedure class="LdapAuthenticator">
  <ldaphost>ldaphost.mydomain</ldaphost>
  <ldapport>389</ldapport>
</procedure>
"""

###
# Checks the proposal password in a LDAP server
###


class LdapAuthenticatorMockup(AbstractAuthenticator):
    def __init__(self, name):
        Procedure.__init__(self, name)
        self.ldapConnection = None

    def init(self):
        ldaphost = self.get_property("ldaphost")

    def authenticate(self, username, password, retry=True):
        return True

    def invalidate(self):
        pass
