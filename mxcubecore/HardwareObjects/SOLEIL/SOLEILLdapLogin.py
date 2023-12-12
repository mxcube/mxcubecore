from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import Procedure
import logging
import ldap
import re
import time

"""
<procedure class="LdapLogin">
  <ldaphost>ldaphost.mydomain</ldaphost> 195.221.10.1
  <ldapport>389</ldapport>
  <ldapdc>EXP</ldapdc>
</procedure>
"""

###
# Checks the proposal password in a LDAP server
###


class SOLEILLdapLogin(Procedure):
    def __init__(self, name):
        Procedure.__init__(self, name)
        self.ldapConnection = None

    # Initializes the hardware object
    def init(self):
        ldaphost = self.get_property("ldaphost")
        ldapdc = self.get_property("ldapdc")
        if ldaphost is None:
            logging.getLogger("HWR").error(
                "LdapLogin: you must specify the LDAP hostname"
            )
        else:
            ldapport = self.get_property("ldapport")

            if ldapport is None:
                logging.getLogger("HWR").debug(
                    "LdapLogin: connecting to LDAP server %s", ldaphost
                )
                self.ldapConnection = ldap.open(ldaphost)
            else:
                logging.getLogger("HWR").debug(
                    "LdapLogin: connecting to LDAP server %s:%s", ldaphost, ldapport
                )
                self.ldapConnection = ldap.open(ldaphost, int(ldapport))
                self.ldapConnection.simple_bind_s()

        if ldapdc is not None:
            parts = ldapdc.split(".")
            self.dcparts = ""
            comma = ""
            for part in parts:
                self.dcparts += "dc=%s%s" % (part, comma)
                comma = ","
        else:
            self.dcparts = "dc=esrf,dc=fr"

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
                    self.ldapConnection = ldap.open(ldaphost)
                    self.ldapConnection.simple_bind_s()
                else:
                    logging.getLogger("HWR").debug(
                        "LdapLogin: reconnecting to LDAP server %s:%s",
                        ldaphost,
                        ldapport,
                    )
                    self.ldapConnection = ldap.open(ldaphost, int(ldapport))
                    self.ldapConnection.simple_bind_s()

    # Logs the error message (or LDAP exception) and returns the respective tuple
    def cleanup(self, ex=None, msg=None):
        if ex is not None:
            try:
                msg = ex[0]["desc"]
            except (IndexError, KeyError, ValueError, TypeError):
                msg = "generic LDAP error"
        logging.getLogger("HWR").debug("LdapLogin: %s" % msg)
        if ex is not None:
            self.reconnect()
        return (False, msg)

    # Check password in LDAP
    def getinfo(self, username):

        found = self.search_user(username)

        if not found:
            return self.cleanup(msg="unknown proposal %s" % username)
        else:
            dn, info = found[0]
            return info

    def login(self, username, password, retry=True):

        if self.ldapConnection is None:
            return self.cleanup(msg="no LDAP server configured")

        found = self.search_user(username, retry)

        if not found:
            return self.cleanup(msg="unknown proposal %s" % username)

        if password == "":
            return self.cleanup(msg="invalid password for %s" % username)

        if not isinstance(found, list):
            logging.getLogger("HWR").error("LdapLogin: found type: %s" % type(found))
            return self.cleanup(msg="unknown error %s" % username)

        # I don't quite understand this -- check whether it works MS 2015-07-14
        for dn, entry in found:
            dn = str(dn)

        logging.getLogger("HWR").debug("LdapLogin: found: %s" % dn)
        logging.getLogger("HWR").debug("LdapLogin: validating %s" % username)
        handle = self.ldapConnection.simple_bind(dn, password)
        try:
            result = self.ldapConnection.result(handle)
        except ldap.INVALID_CREDENTIALS:
            return self.cleanup(msg="invalid password for %s" % username)
        except ldap.LDAPError as err:
            if retry:
                self.cleanup(ex=err)
                return self.login(username, password, retry=False)
            else:
                return self.cleanup(ex=err)
        logging.getLogger("HWR").debug("LdapLogin: searching for %s" % username)

        return (True, username)

    def search_user(self, username, retry=True):

        logging.getLogger("HWR").debug(
            "LdapLogin: searching for %s (dcparts are: %s)" % (username, self.dcparts)
        )

        try:
            found = self.ldapConnection.search_s(
                self.dcparts, ldap.SCOPE_SUBTREE, "uid=" + username
            )
        except ldap.LDAPError as err:
            print("error in LDAP search", err)
            return self.cleanup(ex=err)
        else:
            return found

    def find_groups_for_username(self, username):
        # dcparts = "dc=Exp"
        dcparts = "ou=Projets,ou=Groups,dc=EXP"
        filter = "(&(objectClass=posixGroup)(memberUid=%s))" % username
        groupnames = {}

        # dcparts = "ou=Groups"
        # filter = ""

        found = self.ldapConnection.search_s(dcparts, ldap.SCOPE_SUBTREE, filter)
        for item in found:
            mat = re.search(r"cn=(?P<gname>[^\,]*)\,", item[0])
            if mat:
                groupnames[mat.group("gname")] = item[1]["memberUid"]
        return groupnames

    def find_projectusers(self, username):
        groups = self.find_groups_for_username(username)
        projusers = []
        for groupname, users in groups.items():
            for user in users:
                if user == groupname[1:]:
                    projusers.append(user)
        return projusers

    def find_users_samegroup(self, username):
        pass

    def find_usernames_in_group(self, groupname):
        dcparts = "ou=Projets,ou=Groups,dc=EXP"
        dcparts = "cn=%sou=Projets,ou=Groups,dc=EXP" % groupname
        filter = "((memberUid=*))" % username

    def find_description_for_user(self, username):
        dcparts = "dc=EXP"
        filter = "uid=%s" % username
        found = self.ldapConnection.search_s(dcparts, ldap.SCOPE_SUBTREE, filter)
        try:
            return found[0][1]["description"][0]
        except Exception:
            return None

    def find_sessions_for_user(self, username):
        sesslist = SessionList()
        for projuser in self.find_projectusers(username):
            desc = self.find_description_for_user(projuser)
            if desc is not None:
                sesslist.extend(self.decode_session_info(projuser, desc))
        print("find_sessions_for_user")
        print(sesslist)
        return sesslist

    def find_valid_sessions_for_user(self, username, beamline=None):
        sesslist = self.find_sessions_for_user(username)
        print("find_valid_sessions_for_user(self,username, beamline='proxima2a')")
        print("sesslist")
        print(sesslist)
        return sesslist.find_valid_sessions(beamline=beamline)

    def decode_session_info(self, projuser, session_info):
        """ ext;proxima1:1266393600,1266595200-1265644800,1265846400-1425510000,1426114800 """

        retlist = SessionList()

        beamlinelist = session_info.split(";")

        if len(beamlinelist) < 2:
            print("Cannot parse session info in ldap", session_info)
            return retlist

        usertype = beamlinelist[0]

        try:
            for blsess in beamlinelist[1:]:
                beamline, sessionlist = blsess.split(":")
                sessions = sessionlist.split("-")
                for sess in sessions:
                    sessbeg, sessend = sess.split(",")
                    sessinfo = SessionInfo(
                        projuser, usertype, beamline, int(sessbeg), int(sessend)
                    )
                    retlist.append(sessinfo)
        except Exception:
            print("Cannot parse session info in ldap", session_info)

        return retlist

    def show_all(self):
        try:
            found = self.ldapConnection.search_s(self.dcparts, ldap.SCOPE_SUBTREE)
        except ldap.LDAPError as err:
            print("error in LDAP search", err)
            return self.cleanup(ex=err)
        else:
            for item in found:
                print(item)


class SessionInfo:
    def __init__(self, username, usertype, beamline, sessbeg, sessend):
        self.username = username
        self.usertype = usertype
        self.beamline = beamline
        self.begin = sessbeg
        self.finish = sessend

    def __repr__(self):
        retstr = """
            Beamline: %s; Username: %s (%s); From: %s: To: %s
""" % (
            self.beamline,
            self.username,
            self.usertype,
            time.asctime(time.localtime(self.begin)),
            time.asctime(time.localtime(self.finish)),
        )
        return retstr


class SessionList(list):
    def beamlineList(self):
        retlist = []
        for session in self:
            if session.beamline not in retlist:
                retlist.append(session.beamline)
        return retlist

    def find_valid_sessions(self, timestamp=None, beamline=None):
        print("find_valid_sessions")
        if timestamp is None:
            timestamp = time.time()

        retlist = SessionList()

        for session in self:
            if timestamp >= session.begin and timestamp <= session.finish:
                if beamline is None or beamline.lower() == session.beamline.lower():
                    retlist.append(session)
        print("valid session")
        print(retlist)
        return retlist


def test():
    hwr = HWR.get_hardware_repository()
    hwr.connect()

    conn = hwr.get_hardware_object("/ldapconnection")
    # conn.login("20141015", "4dBM0lx3pw")

    # ok,name = conn.login("99140198", "5u4Twf70K5")
    # ok,name = conn.login("mx20100023", "tisabet")
    # ok,name = conn.login("anything", "tisabet")

    # info = conn.getinfo("legrand")
    # info = conn.getinfo("20100023")
    # conn.find_groups_for_username('houdusse')

    # grps = conn.find_groups_for_username('houdusse')
    # for grp,users in grps.items():
    # print grp, " :  " , users
    user = "20140088"  # '20100023'
    sess = conn.find_sessions_for_user("%s" % user)
    for onesess in sess:
        print("Session for %s" % user, onesess)

    validsess = conn.find_valid_sessions_for_user(user)
    for valid in validsess:
        print("Valid session for today", valid)

    # if info:
    #     print "GID:", info.get('gidNumber','')[0]
    #     print "UID:", info.get('uidNumber','')[0]
    #     print "title:", info.get('title','')


if __name__ == "__main__":
    test()
