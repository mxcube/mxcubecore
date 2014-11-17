from HardwareRepository.BaseHardwareObjects import Procedure
import logging
import ldap

"""
<procedure class="MaxLdapLogin">
  <ldaphost>ldaphost.mydomain</ldaphost>
  <ldapport>389</ldapport>
</procedure>
"""

###
### Checks the proposal password in a LDAP server
###
class MaxLdapLogin(Procedure):
    def __init__(self,name):
        Procedure.__init__(self,name)
        self.ldapConnection=None

    # Initializes the hardware object
    def init(self):
        ldaphost=self.getProperty('ldaphost')
        if ldaphost is None:
            logging.getLogger("HWR").error("MaxLdapLogin: you must specify the LDAP hostname")
        else:
            ldapport=self.getProperty('ldapport')

            if ldapport is None:
                logging.getLogger("HWR").debug("MaxLdapLogin: connecting to LDAP server %s",ldaphost)
                self.ldapConnection=ldap.open(ldaphost)
            else:
                logging.getLogger("HWR").debug("MaxLdapLogin: connecting to LDAP server %s:%s",ldaphost,ldapport)
                self.ldapConnection=ldap.open(ldaphost,int(ldapport))

    # Creates a new connection to LDAP if there's an exception on the current connection
    def reconnect(self):
        if self.ldapConnection is not None:
            try:
                self.ldapConnection.result(timeout=0)
            except ldap.LDAPError,err:
                ldaphost=self.getProperty('ldaphost')
                ldapport=self.getProperty('ldapport')
                if ldapport is None:
                    logging.getLogger("HWR").debug("MaxLdapLogin: reconnecting to LDAP server %s",ldaphost)
                    self.ldapConnection=ldap.open(ldaphost)
                else:
                    logging.getLogger("HWR").debug("MaxLdapLogin: reconnecting to LDAP server %s:%s",ldaphost,ldapport)
                    self.ldapConnection=ldap.open(ldaphost,int(ldapport))
            
    # Logs the error message (or LDAP exception) and returns the respective tuple
    def cleanup(self,ex=None,msg=None):
        if ex is not None:
            try:
                msg=ex[0]['desc']
            except (IndexError,KeyError,ValueError,TypeError):
                msg="generic LDAP error"
        logging.getLogger("HWR").debug("MaxLdapLogin: %s" % msg)
        if ex is not None:
            self.reconnect()
        return (False,msg)

    # Check password in LDAP
    def login(self,username,password,retry=True):
        if self.ldapConnection is None:
            return self.cleanup(msg="no LDAP server configured")

        logging.getLogger("HWR").debug("MaxLdapLogin: searching for %s" % username)
        try:
            found=self.ldapConnection.search_s("ou=People,dc=maxlab,dc=lu,dc=se",\
                ldap.SCOPE_ONELEVEL,"uid="+username,["uid"])
        except ldap.LDAPError,err:
            if retry:
                self.cleanup(ex=err)
                return self.login(username,password,retry=False)
            else:
                return self.cleanup(ex=err)

        if not found:
            return self.cleanup(msg="unknown username %s" % username)
        if password=="":
            return self.cleanup(msg="invalid password for %s" % username)

        logging.getLogger("HWR").debug("MaxLdapLogin: validating %s" % username)
        handle=self.ldapConnection.simple_bind("uid=%s,ou=people,dc=maxlab,dc=lu,dc=se" % username,password)
        try:
            result=self.ldapConnection.result(handle)
        except ldap.INVALID_CREDENTIALS:
            return self.cleanup(msg="invalid password for %s" % username)
        except ldap.LDAPError,err:
            if retry:
                self.cleanup(ex=err)
                return self.login(username,password,retry=False)
            else:
                return self.cleanup(ex=err)

        return (True,username)
