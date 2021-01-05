from mx3core.BaseHardwareObjects import Procedure
import logging

"""
<procedure class="LdapLogin">
  <ldaphost>ldaphost.mydomain</ldaphost>
  <ldapport>389</ldapport>
</procedure>
"""

###
# Checks the proposal password in a LDAP server
###


class LdapLoginMockup(Procedure):
    def __init__(self, name):
        Procedure.__init__(self, name)
        self.ldapConnection = None

    # Initializes the hardware object
    def init(self):
        ldaphost = self.get_property("ldaphost")

    # Check password in LDAP
    def login(self, username, password, retry=True):
        return (True, username)
