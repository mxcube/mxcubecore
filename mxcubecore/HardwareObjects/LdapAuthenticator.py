"""
This module serves to connect to and Ldap server.

It works in principle for ESRF, Soleil Proxima and MAXIV beamlines
"""

import logging

import ldap

from mxcubecore.HardwareObjects.abstract.AbstractAuthenticator import (
    AbstractAuthenticator,
)

"""
ldapou is optional, if ldapou is not defined,
the bind_str (simple_bind) will be "uid=xxx,dc=xx,dc=xx",
otherwise it is uid=xxx,ou=xxx,dc=xx,dc=xx

<procedure class="LdapAuthenticator">
  <ldaphost>ldaphost.mydomain</ldaphost>
  <ldapport>389</ldapport>
  <ldapdomain>example.com</ldapdomain>
  <ldapou>users</ldapou>
</procedure>
"""


class LdapAuthenticator(AbstractAuthenticator):
    def __init__(self, name):
        super().__init__(name)
        self._ldapConnection = None

    # Initializes the hardware object
    def init(self):
        self._field_values = None
        self._connect()

    def _connect(self):
        ldaphost = self.get_property("ldaphost")
        ldapport = self.get_property("ldapport")
        domain = self.get_property("ldapdomain")

        if ldaphost is None:
            logging.getLogger("HWR").error(
                "LdapAuthenticator: you must specify the LDAP hostname"
            )
        else:
            if ldapport is None:
                logging.getLogger("HWR").debug(
                    "LdapAuthenticator: connecting to LDAP server %s", ldaphost
                )
                self._ldapConnection = ldap.initialize("ldap://" + ldaphost)
            else:
                logging.getLogger("HWR").debug(
                    "LdapAuthenticator: connecting to LDAP server %s:%s",
                    ldaphost,
                    ldapport,
                )
                self._ldapConnection = ldap.initialize(
                    "ldap://%s:%s" % (ldaphost, int(ldapport))
                )

            logging.getLogger("HWR").debug(
                "LdapAuthenticator: got connection %s" % str(self._ldapConnection)
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
                "LdapAuthenticator: got connection %s" % str(self._ldapConnection)
            )
        else:
            self.domstr = "dc=esrf,dc=fr"  # default is esrf.fr

    # Creates a new connection to LDAP if there's an exception on the current connection
    def _reconnect(self):
        if self._ldapConnection is not None:
            try:
                self._ldapConnection.result(timeout=0)
            except ldap.LDAPError:
                ldaphost = self.get_property("ldaphost")
                ldapport = self.get_property("ldapport")
                if ldapport is None:
                    logging.getLogger("HWR").debug(
                        "LdapAuthenticator: reconnecting to LDAP server %s", ldaphost
                    )
                    self._connect()
                else:
                    logging.getLogger("HWR").debug(
                        "LdapAuthenticator: reconnecting to LDAP server %s:%s",
                        ldaphost,
                        ldapport,
                    )
                    self._connect()

    def _cleanup(self, ex=None, msg=None):
        if ex is not None:
            try:
                msg = ex[0]["desc"]
            except (IndexError, KeyError, ValueError, TypeError):
                msg = "generic LDAP error"

            self._reconnect()

        logging.getLogger("HWR").info("LdapAuthenticator: %s" % msg)

        return False

    def get_field_values(self):
        return self._field_values

    def invalidate(self):
        pass

    def authenticate(self, username, password, retry=True, fields=None):
        # fields can be used in local implementation to retrieve user information from
        # ldap.  In ALBA for example, it is used to obtain homeDirectory upon successful
        # login and use that value for programming session hwo directories

        self._field_values = None

        if self._ldapConnection is None:
            return self._cleanup(msg="no LDAP server configured")

        logging.getLogger("HWR").debug(
            "LdapAuthenticator: searching for %s / %s" % (username, self.domstr)
        )
        try:
            search_str = self.domstr
            if fields is None:
                found = self._ldapConnection.search_s(
                    search_str, ldap.SCOPE_SUBTREE, "uid=" + username, ["uid"]
                )
            else:
                found = self._ldapConnection.search_s(
                    search_str, ldap.SCOPE_SUBTREE, "uid=" + username, fields
                )
        except ldap.LDAPError as err:
            if retry:
                self._cleanup(ex=err)
                return self.authenticate(username, password, retry=False)
            else:
                return self._cleanup(ex=err)

        if not found:
            return self._cleanup(msg="unknown proposal %s" % username)

        if fields is not None:
            self._field_values = found[0][1]

        if password == "":
            return self._cleanup(msg="invalid password for %s" % username)

        logging.getLogger("HWR").debug("LdapAuthenticator: validating %s" % username)

        try:
            bind_str = "uid=%s, ou=%s, %s" % (username, self.ldapou, self.domstr)
        except AttributeError:
            bind_str = "uid=%s,%s" % (username, self.domstr)

        logging.getLogger("HWR").debug("LdapAuthenticator: binding to %s" % bind_str)
        handle = self._ldapConnection.simple_bind(bind_str, password)

        try:
            self._ldapConnection.result(handle)
        except ldap.INVALID_CREDENTIALS:
            # try second time with different bind_str
            bind_str = "uid=%s, ou=people,%s" % (username, self.domstr)
            handle = self._ldapConnection.simple_bind(bind_str, password)
            try:
                self._ldapConnection.result(handle)
            except Exception:
                return self._cleanup(msg="invalid password for %s" % username)
        except ldap.LDAPError as err:
            if retry:
                self._cleanup(ex=err)
                return self.authenticate(username, password, retry=False)
            else:
                return self._cleanup(ex=err)

        return True
