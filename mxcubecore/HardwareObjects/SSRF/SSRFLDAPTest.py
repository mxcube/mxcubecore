import ldap

def main():

    username = "BLU17UM"
    password = "Zfmc+26$02"
    domstr = "dc=dc3,dc=ssrf,dc=ac,dc=cn"
    bind_str = "cn=%s,%s" % (username, domstr)

    ldapConnection = ldap.initialize("ldap://10.30.43.8")
    print("init done")

    handle = ldapConnection.simple_bind(bind_str, password)
    print("bind done")

    ldapConnection.search_st(domstr, ldap.SCOPE_SUBTREE, "cn="+username, ["cn"], timeout=5)
    print("User found")

    result = ldapConnection.result(handle)
    print("result = ", str(result))


if __name__ == "__main__":
    main()