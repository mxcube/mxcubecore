# $Id: TacoDevice_MTSafe.py,v 1.5 2004/11/15 12:39:19 guijarro Exp $
import types
import weakref
from threading import RLock

from Taco import *

_global_lock = RLock()


def makeThreadSafeMethod(func):
    def threadsafemethod(self, *args, **kwargs):
        self._monitor_lockObj.acquire()
        # print ">>%s: got lock" % func.__name__
        try:
            return func(self, *args, **kwargs)
        finally:
            self._monitor_lockObj.release()
            # print "<<%s: released lock" % func.__name__

    return threadsafemethod


class ThreadSafeMethodsMetaClass(type):
    def __new__(meta, name, bases, dict):
        methods = [
            v
            for k, v in dict.items()
            if isinstance(v, types.FunctionType) and not v.__name__.startswith("__")
        ]
        for m in methods:
            dict[m.__name__] = makeThreadSafeMethod(m)
            dict["_monitor_lockObj"] = _global_lock  # RLock()

        return super(ThreadSafeMethodsMetaClass, meta).__new__(meta, name, bases, dict)


Dev_deb = [0]
# Dev_Exception = "TacoException"
Dev_Exception = RuntimeError


# Tab_dev:
# dictionnary indexed with devices names (in lower case)
#
# { device_name1: { 'cobj' : C object,
# 		    'ref'  : number of references to that object
#                   'cmd'  : { command_name : [cmd,in_type,out_type],
# 		               command_name : [cmd,in_type,out_type],
# 			       ...
# 			     }
# 		  },
#   device_name2: { 'cobj' : C object,
# 		    'ref'  : number of references to that object
#                   'cmd'  : { command_name : [cmd,in_type,out_type],
# 		               command_name : [cmd,in_type,out_type],
# 			       ...
# 			     }
# 		  }
# .....

Tab_dev = {}

# Tab_devC:
# dictionnary indexed with data collector devices names (in lower case)
#
# { device_name1: { 'cobj' : C object,
# 		    'ref'  : number of references to that object
#                   'cmd'  : { command_name : [cmd,out_type],
# 		               command_name : [cmd,out_type],
# 			       ...
# 			     }
# 		  },
#   device_name2: { 'cobj' : C object,
# 		    'ref'  : number of references to that object
#                   'cmd'  : { command_name : [cmd,out_type],
# 		               command_name : [cmd,out_type],
# 			       ...
# 			     }
# 		  }
# .....

# Dictionnary for the correspondance between type number (in ascii
# representation) and a string for user
Tab_dev_type = {
    "0": "void                         ",
    "1": "boolean                      ",
    "70": "unsigned short               ",
    "2": "short                        ",
    "71": "unsigned long                ",
    "3": "long                         ",
    "4": "float                        ",
    "5": "double                       ",
    "6": "string                       ",
    "27": "(long,float)                 ",
    "7": "(float,float)                ",
    "8": "(short,float,float           ",
    "22": "(long,long)                  ",
    "23": "(double,double)              ",
    "9": "list of char                 ",
    "24": "list of string               ",
    "72": "list of unsigned short       ",
    "10": "list of short                ",
    "69": "list of unsigned long        ",
    "11": "list of long                 ",
    "12": "list of float                ",
    "68": "list of double               ",
    "25": "list of (float,float)        ",
    "73": "list of (short,float,float)  ",
    "45": "list of ((long,long)         ",
    "47": "opaque                       ",
    "46": "((8 long),(8 float),(8 long))",
    "54": "(long,long)                  ",
    "55": "(long,float)                 ",
}

Tab_dev_type_unk = "<unknown>                    "
Tab_dev_head = "INPUT:                        OUTPUT:                       COMMAND:"
Tab_devC_head = "OUTPUT:                       COMMAND:"


def dev_debug(flag):
    #  input:
    #     flag: debug flag
    # 	0: no trace
    # 	else: trace
    #
    #  returns:
    # 	- 0: error
    #  	- 1: OK
    # --------------------------------------------------------------
    if not isinstance(flag, int):
        print("dev_debug: parameter not a number")
    else:
        Dev_deb[0] = flag
        if Dev_deb[0] != 0:
            print(" debug mode %d" % Dev_deb[0])


def dev_init(mdevname):
    #  input:
    #     mdevname: device name
    #
    #  returns list:
    # 	- [] if error
    #
    #  	- [devname,cpt]
    #     		devname: mdevname in lowercase
    #     		cpt:  index in C device table
    # --------------------------------------------------------------
    # print 'dev_init: ' + mdevname
    # print Dev_deb[0]
    locname = mdevname.lower()

    #  try to find in Tab_dev list if name already
    #  found

    if locname not in Tab_dev:
        #     have to import the device and create place in dict
        try:
            mpt = esrf_import(locname)
        except Exception:
            #         print error
            #         print "dev_init: error on importing device %s" % locname
            raise Dev_Exception("dev_init: error on importing device %s" % locname)
        else:
            #     create in Tab_dev
            Tab_dev[locname] = {"cobj": mpt}
            Tab_dev[locname]["cmd"] = dev_query(locname)
            if len(Tab_dev[locname]["cmd"]) == 0:
                raise Dev_Exception("Error on importing device %s" % locname)

    if Dev_deb[0] == 1:
        print("dev_init: leaving OK")

    # print locname, Tab_dev[locname]
    return locname, Tab_dev[locname]["cobj"]


def dev_initC(mdevname):
    #  input:
    #     mdevname: device name
    #
    #  returns list:
    # 	- [] if error
    #
    #  	- [devname,cpt]
    #     		devname: mdevname in lowercase
    #     		cpt:  index in C device table
    # --------------------------------------------------------------
    locname = mdevname.lower()

    #  try to find in Tab_dev list if name already
    #  found
    if locname not in Tab_dev:
        #     have to import the device and create place in dict
        try:
            mpt = esrf_dc_import(locname)
        except Exception:
            #         print error
            #         print "dev_initC: error on importing device %s" % locname
            raise Dev_Exception("dev_initC: error on importing device %s" % locname)
        else:
            #     create in Tab_dev
            Tab_dev[locname] = {"cobj": mpt}
            Tab_dev[locname]["cmd"] = dev_queryC(locname)
            if len(Tab_dev[locname]["cmd"]) == 0:
                raise Dev_Exception(
                    "Error on importing data collector device %s" % locname
                )

    if Dev_deb[0] == 1:
        print("dev_initC: leaving OK")

    return locname, Tab_dev[locname]["cobj"]


def dev_query(mdevname):
    """
    input:
    mdevname: device name in lower case

    returns dictionnary:
    - {} if error
    -{cmd_name:[cmd,in_type,out_type], ...}

    cmd_name: command string
    cmd: command numeric value
    in_type: input type
    out_type: output type"""
    if mdevname in Tab_dev:
        loc_c_pt = Tab_dev[mdevname]["cobj"]

        try:
            return esrf_query(loc_c_pt)
        except Exception:
            pass
            # raise Dev_Exception
    else:
        raise Dev_Exception("dev_query: no device %s defined" % mdevname)

    return {}


def dev_queryC(mdevname):
    #   input:
    #      mdevname: device name in lower case
    #
    #   returns dictionnary:
    # 	- {} if error
    #
    #  	-{cmd_name:[cmd,out_type], ...}
    # 	        cmd_name: command string
    #     		cmd: command numeric value
    # 		out_type: output type
    # --------------------------------------------------------------
    try:
        locdict = esrf_dc_info(mdevname)
    except Exception:
        raise Dev_Exception("dev_queryC: error on query for device %s" % mdevname)
        return {}

    return locdict


def dev_tcpudp(mdevname, mode):
    #   input:
    #      	mdevname: device name in lower case
    # 	mode: "tcp" or "udp"
    #
    #   returns value:
    # 	- 0 if error
    #  	- 1 if OK
    # --------------------------------------------------------------
    if mdevname in Tab_dev:
        loc_c_pt = Tab_dev[mdevname]["cobj"]
        if Dev_deb[0] == 1:
            print(loc_c_pt)
        if (mode != "tcp") and (mode != "udp"):
            print("usage: dev_tcpudp(<device_name>,udp|tcp)")
            return 0
        try:
            ret = esrf_tcpudp(loc_c_pt, mode)
        except Exception:
            raise Dev_Exception(
                "dev_tcpudp: error on esrf_tcpudp for device %s" % mdevname
            )
            return 0
    else:
        print("dev_tcpudp: no device %s defined" % mdevname)
        return 0

    return 1


def dev_timeout(mdevname, *mtime):
    #   input:
    #      	mdevname: device name in lower case
    # 	mtime: optional argument:
    # 		- if not existing: read timeout required
    # 		- if exists: time in  second for setting timeout
    #
    #   returns value:
    # 	- 0 if error
    # 	- time in sec (read or set) if OK
    # --------------------------------------------------------------
    if mdevname in Tab_dev:
        loc_c_pt = Tab_dev[mdevname]["cobj"]
        if Dev_deb[0] == 1:
            print(loc_c_pt)
        if mtime == ():
            print("dev_timeout readmode ")
            try:
                ret = esrf_timeout(loc_c_pt)
            except Exception:
                raise Dev_Exception("error on esrf_timeout for device " + mdevname)
                return 0
            return ret
        else:
            itime = mtime[0]
            if isinstance(itime, int) or isinstance(itime, float):
                print("dev_timeout set mode %f" % itime)
                try:
                    ret = esrf_timeout(loc_c_pt, itime)
                except Exception:
                    raise Dev_Exception("error on esrf_timeout for device " + mdevname)
                    return 0
                return ret
    else:
        print("dev_timeout: no device %s defined" % mdevname)
        return 0


def dev_getresource(mdevname, resname):
    #   input:
    #      	mdevname: device name
    # 	resname:  resource name
    #
    #   returns value packed as a string:
    # 	- resource value if OK
    # 	- None if error
    # --------------------------------------------------------------
    try:
        ret = esrf_getresource(mdevname, resname)
    except Exception:
        raise Dev_Exception(
            "dev_getresource: error for device %s on resource %s" % (mdevname, resname)
        )
        return None
    if Dev_deb[0] == 1:
        print("string length is %s" % len(ret))
    return ret


def dev_putresource(mdevname, resname, value):
    #   Sets a device resource
    #   input:
    #      	mdevname: device name
    # 	resname:  resource name
    # 	value: the resource value packed as a string
    #
    #   returns value:
    # 	- 1: if OK
    # 	- 0: if error
    # --------------------------------------------------------------
    if not isinstance(value, bytes):
        print("dev_putresource: resource value must be packed as string")
    try:
        ret = esrf_putresource(mdevname, resname, value)
    except Exception:
        raise Dev_Exception(
            "dev_putresource: error for device %s on resource %s" % (mdevname, resname)
        )
        return 0
    return 1


def dev_delresource(mdevname, resname):
    #   removes a device resource
    #   input:
    #      	mdevname: device name
    # 	resname:  resource name
    #
    #   returns value:
    # 	- 1: OK
    # 	- 0: error
    # --------------------------------------------------------------
    try:
        ret = esrf_delresource(mdevname, resname)
    except Exception:
        raise Dev_Exception(
            "dev_delresource: error for device %s on resource %s" % (mdevname, resname)
        )
        return 0
    return 1


def dev_io(mdevname, mdevcommand, *parin, **kw):
    #   input:
    #      	mdevname: device name in lower case
    # 	parin: list of optional INPUT parameters
    # 	kw: dictionnary of optional OUTPUT parameters
    #
    #   returns value:
    # 	- 1 : if no device ARGOUT or OUTPUT param provided
    # 	- device ARGOUT : if device ARGOUT and no OUTPUT param
    #
    #   in case of error, global variable DEV_ERR is set to 1
    if Dev_deb[0] == 1:
        print("in dev_io")

    try:
        loc_c_pt = Tab_dev[mdevname]["cobj"]
    except KeyError:
        raise Dev_Exception("dev_io: no device %s defined" % mdevname)
    else:
        if Dev_deb[0] == 1:
            print(loc_c_pt)
            print("  devname : " + mdevname)
            print("  command : " + mdevcommand)
            print("  parin : %s" % (parin,))
            print("  kw : %s" % (kw,))

        try:
            io_cmd = Tab_dev[mdevname]["cmd"][mdevcommand][0]
            io_in = Tab_dev[mdevname]["cmd"][mdevcommand][1]
            io_out = Tab_dev[mdevname]["cmd"][mdevcommand][2]
        except KeyError:
            raise AttributeError(
                "dev_io: no command %s for device %s" % (mdevcommand, mdevname)
            )
        else:
            if len(parin) == 1:
                if isinstance(parin[0], tuple):
                    parin = parin[0]
                elif isinstance(parin[0], list):
                    parin = tuple(parin[0])

            if Dev_deb[0] == 1:
                print("esrf_io arg:")
                print(
                    (Tab_dev[mdevname]["cobj"], mdevcommand, io_cmd, io_in, io_out, 0)
                    + (parin,)
                )
                print("esrf_io dict:")
                print(kw)

            try:
                ret = esrf_io(
                    Tab_dev[mdevname]["cobj"],
                    mdevcommand,
                    io_cmd,
                    io_in,
                    io_out,
                    0,
                    parin,
                    **kw
                )
            except Exception:
                raise Dev_Exception(
                    "Cannot execute esrf_io %s,%s" % (mdevname, mdevcommand)
                )
            else:
                return ret


def dev_ioC(mdevname, mdevcommand, **kw):
    #   input:
    #      	mdevname: device name in lower case
    # 	kw: dictionnary of optional OUTPUT parameters
    #
    #   returns value:
    # 	- 1 : if no device ARGOUT or OUTPUT param provided
    # 	- device ARGOUT : if device ARGOUT and no OUTPUT param
    #
    #   in case of error, global variable DEV_ERR is set to 1
    # --------------------------------------------------------------
    if Dev_deb[0] == 1:
        print("in dev_ioC")
    if mdevname in Tab_dev:
        loc_c_pt = Tab_dev[mdevname]["cobj"]
        if Dev_deb[0] == 1:
            print(loc_c_pt)
            print("  devname : " + mdevname)
            print("  command : " + mdevcommand)
            print("  kw : %s" % (kw,))
        #  check now that parameters are correct

        #  then run the esrf_io commnd
        #  first check that command exists:
        if mdevcommand in Tab_dev[mdevname]["cmd"]:
            io_cmd = Tab_dev[mdevname]["cmd"][mdevcommand][0]
            io_in = 0  # void
            io_out = Tab_dev[mdevname]["cmd"][mdevcommand][1]
            parin2 = (
                Tab_dev[mdevname]["cobj"],
                mdevcommand,
                io_cmd,
                io_in,
                io_out,
                1,
            ) + ((),)
            if Dev_deb[0] == 1:
                print("esrf_io arg:")
                print(parin2)
                print("esrf_io dict:")
                print(kw)
            ret = None
            try:
                # 	    kw={'out':2}
                # 	    kw = {}
                ret = esrf_io(*parin2, **kw)

                if Dev_deb[0] == 1:
                    print("returned from esrf_io: %s" % ret)
            except Exception:
                raise Dev_Exception("esrf_ioC: error on device %s" % mdevname)
            return ret
        else:
            print("dev_ioC: no command %s for device %s" % (mdevcommand, mdevname))

    else:
        print("dev_ioC: no device %s defined" % mdevname)


class TacoCall:
    def __init__(self, devname, command):
        self.devname = devname
        self.command = command

    def __repr__(self):
        return "<TacoCall object %d: device %r, cmd %r>" % (
            id(self),
            self.devname,
            self.command,
        )

    def __call__(self, *args, **kwargs):
        try:
            _global_lock.acquire()

            if Dev_deb[0] == 1:
                print("in device_io")
                print((self.devname, self.command) + (args,) + (kwargs,))

            return dev_io(self.devname, self.command, *args, **kwargs)
        finally:
            _global_lock.release()


class TacoCallC:
    def __init__(self, devname, command):
        self.devname = devname
        self.command = command

    def __call__(self, *args, **kwargs):
        try:
            _global_lock.acquire()

            if Dev_deb[0] == 1:
                print("in device_io")
                print((self.devname, self.command) + (args,) + (kwargs,))

            return dev_ioC(self.devname, self.command, *args, **kwargs)
        finally:
            _global_lock.release()


_tacoDevices = {}


def TacoDevice(name, dc=False):
    try:
        dev = _TacoDevice(name, dc)
    except Exception as err:
        print(err)
        return None
    else:
        dev.imported = 1

        def deviceDestroyed(ref, name=dev.devname):
            del _tacoDevices[name][_tacoDevices[name].index(ref)]

            if len(_tacoDevices[name]) == 0:
                del Tab_dev[name]

        try:
            _tacoDevices[dev.devname].append(weakref.ref(dev, deviceDestroyed))
        except KeyError:
            _tacoDevices[dev.devname] = [weakref.ref(dev, deviceDestroyed)]

        return dev


class _TacoDevice(object):
    __metaclass__ = ThreadSafeMethodsMetaClass

    def __init__(self, name, dc=False):  # constructor
        # print 'Welcome ' + name
        self.__dc = dc

        try:
            self._monitor_lockObj.acquire()

            self.devname = name
            self.imported = 0

            if dc:
                Listout = dev_initC(name)
            else:
                Listout = dev_init(name)
            self.devname = Listout[0]
            self.ds_object = Listout[1]

            if Dev_deb[0] == 1:
                print(self.devname)
        finally:
            self._monitor_lockObj.release()

    def __str__(self):  # for print
        print("ds device:         " + self.devname)
        print(" imported: %d" % self.imported)
        print(" device object : ")
        print(self.ds_object)
        return "0"

    def CommandList(self):
        if self.__dc:
            locdict = dev_queryC(self.devname)
            print(Tab_devC_head)
        else:
            locdict = dev_query(self.devname)
            print(Tab_dev_head)

        if len(locdict) > 0:
            for mykey in list(locdict.keys()):
                my_stringtype_in = "%d" % locdict[mykey][1]
                my_stringtype_out = "%d" % locdict[mykey][2]
                if my_stringtype_in in Tab_dev_type:
                    myin = Tab_dev_type[my_stringtype_in]
                else:
                    myin = Tab_dev_type_unk
                if my_stringtype_out in Tab_dev_type:
                    myout = Tab_dev_type[my_stringtype_out]
                else:
                    myout = Tab_dev_type_unk
                print("%s %s %s" % (myin, myout, mykey))

    def tcp(self):
        if self.imported == 1:
            ret = dev_tcpudp(self.devname, "tcp")
            if ret == 0:
                print("error setting tcp on object" + self.devname)

    def udp(self):
        if self.imported == 1:
            ret = dev_tcpudp(self.devname, "udp")
            if ret == 0:
                print("error setting udp on object" + self.devname)

    def timeout(self, *mtime):
        if self.imported == 1:
            if mtime == ():
                ret = dev_timeout(self.devname)
                if Dev_deb[0] == 1:
                    print("timeout: %f" % ret)
                return ret
            else:
                ret = dev_timeout(self.devname, mtime[0])
                return ret

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        else:
            try:
                self._monitor_lockObj.acquire()

                try:
                    test_if_command_exists = Tab_dev[self.devname]["cmd"][name][0]
                except KeyError:
                    raise AttributeError(name)
                else:
                    if self.__dc:
                        newTacoCall = TacoCallC(self.devname, name)
                    else:
                        newTacoCall = TacoCall(self.devname, name)
                    self.__dict__[name] = newTacoCall
                    return newTacoCall
            finally:
                self._monitor_lockObj.release()
