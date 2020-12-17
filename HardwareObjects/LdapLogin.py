"""
This module serves to connect to and Ldap server.

It works in principle for ESRF, Soleil Proxima and MAXIV beamlines
"""
from mx3core.BaseHardwareObjects import Procedure
import logging
import ldap

"""
ldapou is optional, if ldapou is not defined,
the bind_str (simple_bind) will be "uid=xxx,dc=xx,dc=xx",
otherwise it is uid=xxx,ou=xxx,dc=xx,dc=xx

<procedure class="LdapLogin">
  <ldaphost>ldaphost.mydomain</ldaphost>
  <ldapport>389</ldapport>
  <ldapdomain>example.com</ldapdomain>
  <ldapou>users</ldapou>
</procedure>
"""

###
# Checks the proposal password in a LDAP server
###


class LdapLogin(Procedure):
    def __init__(self, name):
        Procedure.__init__(self, name)
        self.ldapConnection = None

    # Initializes the hardware object
    def init(self):
        self.field_values = None
        self.connect()

    def connect(self):
        ldaphost = self.get_property("ldaphost")
        ldapport = self.get_property("ldapport")
        domain = self.get_property("ldapdomain")
        ldapou = self.get_property("ldapou")

        if ldaphost is None:
            logging.getLogger("HWR").error(
                "LdapLogin: you must specify the LDAP hostname"
            )
        else:
            if ldapport is None:
                logging.getLogger("HWR").debug(
                    "LdapLogin: connecting to LDAP server %s", ldaphost
                )
                self.ldapConnection = ldap.initialize("ldap://" + ldaphost)
            else:
                logging.getLogger("HWR").debug(
                    "LdapLogin: connecting to LDAP server %s:%s", ldaphost, ldapport
                )
                self.ldapConnection = ldap.initialize(
                    "ldap://%s:%s" % (ldaphost, int(ldapport))
                )

            logging.getLogger("HWR").debug(
                "LdapLogin: got connection %s" % str(self.ldapConnection)
            )

        if domain is not None:
            domparts = domain.split(".")
            domstr = ""
            comma = ""
            for part in domparts:
                domstr += "%sdc=%s" % (comma, part)
                comma = ","
            self.domstr = domstr
            logging.getLogger("HWR").debug(
                "LdapLogin: got connection %s" % str(self.ldapConnection)
            )
        else:
            self.domstr = "dc=esrf,dc=fr"  # default is esrf.fr

    # Creates a new connection to LDAP if there's an exception on the current connection
    def reconnect(self):
        if self.ldapConnection is not None:
            try:
                self.ldapConnection.result(timeout=0)
            except ldap.LDAPError as err:
                ldaphost = self.get_property("ldaphost")
                ldapport = self.get_property("ldapport")
                if ldapport is None:
                    logging.getLogger("HWR").debug(
                        "LdapLogin: reconnecting to LDAP server %s", ldaphost
                    )
                    self.connect()
                else:
                    logging.getLogger("HWR").debug(
                        "LdapLogin: reconnecting to LDAP server %s:%s",
                        ldaphost,
                        ldapport,
                    )
                    self.connect()

    # Logs the error message (or LDAP exception) and returns the respective tuple
    def cleanup(self, ex=None, msg=None):
        if ex is not None:
            try:
                msg = ex[0]["desc"]
            except (IndexError, KeyError, ValueError, TypeError):
                msg = "generic LDAP error"

            logging.getLogger("HWR").debug("LdapLogin: %s" % msg)

            self.reconnect()

        return (False, msg)

    # Check password in LDAP
    def login(self, username, password, retry=True, fields=None):
        # fields can be used in local implementation to retrieve user information from
        # ldap.  In ALBA for example, it is used to obtain homeDirectory upon successful
        # login and use that value for programming session hwo directories

        self.field_values = None

        if self.ldapConnection is None:
            return self.cleanup(msg="no LDAP server configured")

        logging.getLogger("HWR").debug(
            "LdapLogin: searching for %s / %s" % (username, self.domstr)
        )
        try:
            search_str = self.domstr
            if fields is None:
                found = self.ldapConnection.search_s(
                    search_str, ldap.SCOPE_SUBTREE, "uid=" + username, ["uid"]
                )
            else:
                found = self.ldapConnection.search_s(
                    search_str, ldap.SCOPE_SUBTREE, "uid=" + username, fields
                )
        except ldap.LDAPError as err:
            if retry:
                self.cleanup(ex=err)
                return self.login(username, password, retry=False)
            else:
                return self.cleanup(ex=err)

        if not found:
            return self.cleanup(msg="unknown proposal %s" % username)

        if fields is not None:
            self.field_values = found[0][1]

        if password == "":
            return self.cleanup(msg="invalid password for %s" % username)

        logging.getLogger("HWR").debug("LdapLogin: validating %s" % username)
        try:
            bind_str = "uid=%s, ou=%s, %s" % (username, self.ldapou, self.domstr)
        except AttributeError as attr:
            bind_str = "uid=%s,%s" % (username, self.domstr)
        logging.getLogger("HWR").debug("LdapLogin: binding to %s" % bind_str)
        handle = self.ldapConnection.simple_bind(bind_str, password)
        try:
            result = self.ldapConnection.result(handle)
        except ldap.INVALID_CREDENTIALS:
            # try second time with different bind_str
            bind_str = "uid=%s, ou=people,%s" % (username, self.domstr)
            handle = self.ldapConnection.simple_bind(bind_str, password)
            try:
                result = self.ldapConnection.result(handle)
            except Exception:
                return self.cleanup(msg="invalid password for %s" % username)
        except ldap.LDAPError as err:
            if retry:
                self.cleanup(ex=err)
                return self.login(username, password, retry=False)
            else:
                return self.cleanup(ex=err)

        return (True, username)

    def get_field_values(self):
        return self.field_values
