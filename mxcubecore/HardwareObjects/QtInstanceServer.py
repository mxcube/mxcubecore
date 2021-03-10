from mxcubecore.BaseHardwareObjects import Procedure
import logging
import time
import pickle
import os
import gevent
import gevent.server
import socket
import pwd

from mxcubecore.utils import qt_import

"""
<procedure class="InstanceServer">
  <host>myhostname</host>
  <port>myport</port>
</procedure>
"""

TERMINATOR = "\0"
INSTANCE_HO = None
SERVER_CLIENTS = {}
CLIENTS = {}

###
# Creates an asynchronous TCP server to manage multiple application instances
###


class QtInstanceServer(Procedure):
    # Initializes the hardware object
    def init(self):
        # Read the HO configuration
        self.serverPort = self.get_property("port")
        self.serverHost = self.get_property("host")
        if self.serverHost is None:
            self.serverHost = socket.getfqdn("")
        self.asyncServer = None
        self.instanceClient = None
        self.guiConfiguration = None

        self.idCount = {}  # server only
        self.clients = {}  # server only

        # self.serverId = None # to remove
        # self.controlId = None # to remove
        # self.myProposal = None # to remove

        self.clientId2 = [None, None]  # client only
        self.serverId2 = [None, None]  # client AND server
        self.controlId2 = [None, None]  # client AND server

        self.bricksEventCache = {}

        global INSTANCE_HO
        INSTANCE_HO = self

        # Check the HO configuration
        if self.serverPort is None:
            logging.getLogger("HWR").error(
                "InstanceServer: you must specify a port number"
            )
        else:
            pass

    def initialize_instance(self):
        for widget in qt_import.QApplication.allWidgets():
            try:
                if hasattr(widget, "configuration"):
                    self.guiConfiguration = widget.configuration
                    break
            except NameError:
                logging.getLogger().warning(
                    "Widget {} has no attribute {}".format(widget, "configuration")
                )

        self.emit("instanceInitializing", ())
        if self.isLocal():
            self.startServer()
        else:
            self.connectToServer()

    #
    def setProposal(self, proposal):
        if self.isServer():
            my_id = self.serverId2[0]
            old_proposal = self.serverId2[1]

            msg = NewClientInstanceMessage()
            msg.setClientId(my_id)
            msg.setAvailable(True)
            msg.setProposal(old_proposal)
            msg.setNewProposal(proposal)
            data = msg.encode()
            broadcast_to_clients(data)

            self.serverId2[1] = proposal
            if self.controlId2[0] == my_id:
                self.controlId2[1] = proposal
        elif self.isClient():
            my_id = self.clientId2[0]

            msg = NewClientInstanceMessage()
            msg.setNewProposal(proposal)
            data = msg.encode()
            send_data_to_server(self.instanceClient, data)

            self.clientId2[1] = proposal
            if self.controlId2[0] == my_id:
                self.controlId2[1] = proposal

    def idPrettyPrint(self, user_id, use_proposal=True):
        my_nick = ""
        pretty_print = ""
        if self.isServer():
            my_nick = self.serverId2[0]
        elif self.isClient():
            my_nick = self.clientId2[0]
        else:
            logging.getLogger("HWR").warning(
                "InstanceServer: printing an id while not server nor client"
            )

        if user_id is None:
            pretty_print = my_nick
        else:
            nick = user_id[0]
            prop = user_id[1]
            if my_nick != nick:
                if use_proposal:
                    if prop is not None:
                        pretty_print = "[%s%s]%s" % (prop["code"], prop["number"], nick)
                    else:
                        pretty_print = "[?]%s" % nick
                else:
                    pretty_print = nick
            else:
                pretty_print = my_nick

        return pretty_print

    # Starts the server
    def startServer(self):
        if self.asyncServer is not None:
            logging.getLogger("HWR").error("InstanceServer: server already started")
        elif self.serverPort is not None:
            try:
                async_server = gevent.server.StreamServer(
                    (self.serverHost, self.serverPort), handleRemoteClient
                )  # AsyncServer(self,self.serverHost,self.serverPort)
                async_server.start()
            except Exception:
                logging.getLogger("HWR").warning(
                    "InstanceServer: cannot create server, so trying to connect to it"
                )
                self.connectToServer()
            else:
                self.asyncServer = async_server
                server_hostname = self.serverHost.split(".")[0]
                logging.getLogger("HWR").debug(
                    "InstanceServer: listening to connections on %s:%d"
                    % (server_hostname, self.serverPort)
                )

                self.serverId2[0] = server_hostname
                self.controlId2 = list(self.serverId2)

                self.idCount[server_hostname] = 1

                self.emit("serverInitialized", (True, self.serverId2))
        else:
            logging.getLogger("HWR").error(
                "InstanceServer: not property configured to start the server"
            )
            self.emit("serverInitialized", (False,))

    # Closes the server
    def closeServer(self):
        self.asyncServer.close()
        self.asyncServer = None

    def connectToServer(self, quiet=False):
        self.emit("clientInitialized", (None,))
        self.reconnect(quiet)

    # Connects to the server
    def reconnect(self, quiet=False):
        try:
            self.instanceClient = InstanceClient(self.serverHost, self.serverPort)
        except Exception:
            self.instanceClient = None
            if not quiet:
                logging.getLogger("HWR").error(
                    "InstanceServer: cannot connect to server"
                )
            self.emit("clientInitialized", (False, (None, None), None, quiet))
        else:
            my_login = pwd.getpwuid(os.getuid())[0]
            msg = AskPermissionInstanceMessage()

            msg.setClientId(my_login)
            msg.setProposal(self.clientId2[1])
            data = msg.encode()

            send_data_to_server(self.instanceClient, data)

    def isLocal(self):
        try:
            display = os.environ["DISPLAY"].split(":")[0]
        except Exception:
            return False
        if not display:
            return True
        return socket.getfqdn(display) == self.serverHost

    def isServer(self):
        return self.asyncServer is not None

    def isClient(self):
        return self.instanceClient is not None

    def inControl(self):
        return self.controlId2

    def serverClosed(self):
        logging.getLogger("HWR").error(
            "InstanceServer: server has closed the connection!"
        )
        self.emit("serverClosed", (self.serverId2,))

    def clientConnected(self, addr, req_handler):
        return

    def clientClosed(self, addr):
        # print "CLIENT CLOSED",addr,self.clients
        found_id = None
        found_prop = None
        for cli_id in self.clients:
            cli_addr = self.clients[cli_id][0]
            cli_prop = self.clients[cli_id][1]
            if cli_addr == addr:
                self.clients.pop(cli_id)
                found_id = cli_id
                found_prop = cli_prop
                self.emit("clientClosed", ((cli_id, cli_prop),))
                break

        if found_id is not None:
            msg = NewClientInstanceMessage()
            msg.setClientId(found_id)
            msg.setProposal(found_prop)
            msg.setAvailable(False)
            data = msg.encode()
            broadcast_to_clients(data)

            if self.controlId2[0] == found_id:
                self.controlId2 = list(self.serverId2)

                msg = PassControlInstanceMessage()
                msg.setClientId(self.controlId2[0])
                msg.setProposal(self.controlId2[1])
                data = msg.encode()
                broadcast_to_clients(data)

                self.emit("haveControl", (True,))

    def requestIdChange(self, new_id):
        if self.isServer():
            msg = NewClientInstanceMessage()

            try:
                count = self.idCount[new_id]
            except KeyError:
                self.idCount[new_id] = 1
            else:
                count += 1
                self.idCount[new_id] = count
                new_id = "%s-%d" % (new_id, count)
                self.idCount[new_id] = 1

            msg.setClientNewId(new_id)
            msg.setClientId(self.serverId2[0])
            msg.setAvailable(True)
            msg.setProposal(self.serverId2[1])
            data = msg.encode()
            broadcast_to_clients(data)

            old_id = self.serverId2[0]
            old_prop = self.serverId2[1]
            self.serverId2[0] = new_id
            if self.controlId2[0] == old_id:
                self.controlId2[0] = new_id
            new_prop = old_prop

            self.emit("clientChanged", ((old_id, old_prop), (new_id, new_prop)))

        elif self.isClient():
            msg = NewClientInstanceMessage()
            msg.setClientNewId(new_id)
            data = msg.encode()
            send_data_to_server(self.instanceClient, data)
        else:
            logging.getLogger("HWR").warning(
                "InstanceServer: requestIdChange while not server nor client!"
            )

    def sendChatMessage(self, priority, message):
        msg = ChatInstanceMessage()
        msg.setChatMessage(priority, message)
        if self.isServer():
            msg.setChatNick(self.serverId2[0])
            msg.setProposal(self.serverId2[1])
            my_id = self.serverId2
        data = msg.encode()
        if self.isServer():
            broadcast_to_clients(data)
        elif self.isClient():
            send_data_to_server(self.instanceClient, data)
            my_id = self.clientId2
        else:
            logging.getLogger("HWR").warning(
                "InstanceServer: sendChatMessage while not server nor client!"
            )
        self.emit("chatMessageReceived", (priority, my_id, message))

    def addEventToCache(self, brick_name, widget_name, message_data):
        self.bricksEventCache[(brick_name, widget_name)] = message_data

    def synchronizeClientWithEvents(self, client_addr):
        for event_data in list(self.bricksEventCache.values()):
            send_data_to_client(client_addr, event_data)

    def sendBrickUpdateMessage(
        self, brick_name, widget_name, widget_method, widget_method_args, masterSync
    ):
        msg = BrickUpdateInstanceMessage()
        msg.setBrickUpdate(
            brick_name, widget_name, widget_method, widget_method_args, masterSync
        )
        data = msg.encode()
        if self.isServer():
            self.addEventToCache(brick_name, widget_name, data)
            broadcast_to_clients(data)
        elif self.isClient():
            send_data_to_server(self.instanceClient, data)
        else:
            logging.getLogger("HWR").warning(
                "InstanceServer: sendBrickUpdateMessage while not server nor client!"
            )

    def sendTabUpdateMessage(self, tab_name, tab_index):
        msg = TabUpdateInstanceMessage()
        msg.setTabUpdate(tab_name, tab_index)
        data = msg.encode()
        self.addEventToCache(None, tab_name, data)
        if self.isServer():
            broadcast_to_clients(data)
        elif self.isClient():
            send_data_to_server(self.instanceClient, data)
        else:
            logging.getLogger("HWR").warning(
                "InstanceServer: sendTabUpdateMessage while not server nor client!"
            )

    def giveControl(self, client_id):
        if self.isServer():
            try:
                client_addr = self.clients[client_id[0]][0]
            except KeyError:
                pass
            else:
                client_prop = self.clients[client_id[0]][1]
                self.controlId2 = [client_id[0], client_prop]

                msg = ControlInstanceMessage()
                msg.setHasControl(True)
                data = msg.encode()
                send_data_to_client(client_addr, data)

                msg = PassControlInstanceMessage()
                msg.setClientId(client_id[0])
                msg.setProposal(client_prop)
                data = msg.encode()
                broadcast_to_clients(data, avoid=(client_addr,))

                self.emit("passControl", ((client_id[0], client_prop),))
                self.emit("haveControl", (False,))

        elif self.isClient():
            msg = PassControlInstanceMessage()
            msg.setClientId(client_id[0])
            msg.setProposal(client_id[1])
            data = msg.encode()
            send_data_to_server(self.instanceClient, data)
        else:
            logging.getLogger("HWR").warning(
                "InstanceServer: giveControl while not server nor client!"
            )

    def askForControl(self):
        msg = AskControlInstanceMessage()
        if self.isClient():
            data = msg.encode()
            send_data_to_server(self.instanceClient, data)
        else:
            msg.setClientId(self.serverId2[0])
            msg.setProposal(self.serverId2[1])
            data = msg.encode()
            broadcast_to_clients(data)

    def takeControl(self):
        if self.isServer():
            if self.controlId2[0] != self.serverId2[0]:
                client_addr = self.clients[self.controlId2[0]][0]
                msg = ControlInstanceMessage()
                msg.setHasControl(False)
                data = msg.encode()
                send_data_to_client(client_addr, data)

                self.controlId2 = list(self.serverId2)

                msg = PassControlInstanceMessage()
                msg.setClientId(self.controlId2[0])
                msg.setProposal(self.controlId2[1])
                data = msg.encode()
                broadcast_to_clients(data)

                self.emit("haveControl", (True,))
            else:
                logging.getLogger("HWR").warning(
                    "InstanceServer: takeControl while already in control!"
                )

        elif self.isClient():
            if self.controlId2[0] != self.clientId2[0]:
                msg = TakeControlInstanceMessage()
                data = msg.encode()
                send_data_to_server(self.instanceClient, data)
            else:
                logging.getLogger("HWR").warning(
                    "InstanceServer: takeControl while already in control!"
                )

    def callInControl(self, brick, method, method_args):
        msg = BrickCallInstanceMessage()
        brick_name = brick.name()
        widget_name = ""
        msg.setBrickUpdate(brick_name, widget_name, method, method_args)
        data = msg.encode()
        if self.isServer():
            if self.controlId2[0] != self.serverId2[0]:
                client_addr = self.clients[self.controlId2[0]][0]
                send_data_to_client(client_addr, data)
            else:
                logging.getLogger("HWR").warning(
                    "InstanceServer: calling a brick while having control!"
                )
        else:
            logging.getLogger("HWR").warning(
                "InstanceServer: only the server can call a brick!"
            )

    def answerToServer(self, brick, method, method_args):
        msg = BrickCallInstanceMessage()
        brick_name = brick.name()
        widget_name = ""
        msg.setBrickUpdate(brick_name, widget_name, method, method_args)
        data = msg.encode()
        if self.isServer():
            logging.getLogger("HWR").warning(
                "InstanceServer: only a client can answer to the server!"
            )
        else:
            data = msg.encode()
            send_data_to_server(self.instanceClient, data)

    def parseReceivedMessage(self, data):
        # logging.getLogger().debug("******** RECEIVED MESSAGE = %r", data)
        msg_obj = None
        try:
            message = InstanceMessage(data=data)
        except Exception:
            logging.getLogger("HWR").exception(
                "InstanceServer: problem parsing received message"
            )
        else:
            try:
                t = message.getType()
            except Exception:
                logging.getLogger("HWR").exception(
                    "InstanceServer: problem parsing received message"
                )
            else:
                if t == InstanceMessage.TYPE_CHAT:
                    msg_obj = ChatInstanceMessage(message)
                elif t == InstanceMessage.TYPE_CONTROL:
                    msg_obj = ControlInstanceMessage(message)
                elif t == InstanceMessage.TYPE_ASKPERMISSION:
                    msg_obj = AskPermissionInstanceMessage(message)
                elif t == InstanceMessage.TYPE_GIVEPERMISSION:
                    msg_obj = GivePermissionInstanceMessage(message)
                elif t == InstanceMessage.TYPE_NEWCLIENT:
                    msg_obj = NewClientInstanceMessage(message)
                elif t == InstanceMessage.TYPE_ASKCONTROL:
                    msg_obj = AskControlInstanceMessage(message)
                elif t == InstanceMessage.TYPE_PASSCONTROL:
                    msg_obj = PassControlInstanceMessage(message)
                elif t == InstanceMessage.TYPE_BRICKUPDATE:
                    msg_obj = BrickUpdateInstanceMessage(message)
                elif t == InstanceMessage.TYPE_TABUPDATE:
                    msg_obj = TabUpdateInstanceMessage(message)
                elif t == InstanceMessage.TYPE_TAKECONTROL:
                    msg_obj = TakeControlInstanceMessage(message)
                elif t == InstanceMessage.TYPE_BRICKCALL:
                    msg_obj = BrickCallInstanceMessage(message)
                else:
                    logging.getLogger("HWR").warning(
                        "InstanceServer: unknown message type %s " % str(t)
                    )
        return msg_obj

    def clientMessageReceived(self, data):
        m = self.parseReceivedMessage(data)
        if m is None:
            return

        if isinstance(m, ChatInstanceMessage):
            self.emit(
                "chatMessageReceived",
                (
                    m.getChatPriority(),
                    (m.getChatNick(), m.getProposal()),
                    m.getChatMessage(),
                ),
            )
        elif isinstance(m, ControlInstanceMessage):
            has_control = m.getHasControl()
            self.emit("haveControl", (has_control,))

        elif isinstance(m, NewClientInstanceMessage):
            client_id = m.getClientId()
            client_proposal = m.getProposal()

            try:
                new_client_id = m.getClientNewId()
            except KeyError:

                try:
                    new_proposal = m.getNewProposal()
                except KeyError:

                    a = m.getAvailable()
                    if a:
                        self.emit("newClient", ((client_id, client_proposal),))
                    else:
                        self.emit("clientClosed", ((client_id, client_proposal),))
                else:
                    if client_id == self.serverId2[0]:
                        self.serverId2[1] = new_proposal
                    self.emit(
                        "clientChanged",
                        ((client_id, client_proposal), (client_id, new_proposal)),
                    )

            else:
                if client_id == self.serverId2[0]:
                    self.serverId2[0] = new_client_id
                self.emit(
                    "clientChanged",
                    ((client_id, client_proposal), (new_client_id, client_proposal)),
                )

        elif isinstance(m, GivePermissionInstanceMessage):
            self.serverId2 = [m.getServerId(), m.getProposal()]

            self.clientId2[0] = m.getClientId()

            self.emit(
                "clientInitialized",
                (True, (m.getServerId(), m.getProposal()), m.getClientId()),
            )

        elif isinstance(m, AskControlInstanceMessage):
            client_id = m.getClientId()
            try:
                client_prop = m.getProposal()
            except Exception:
                client_prop = None
            self.emit("wantsControl", ((client_id, client_prop),))

        elif isinstance(m, PassControlInstanceMessage):
            client_id = m.getClientId()
            client_proposal = m.getProposal()
            self.controlId2 = [client_id, client_proposal]
            self.emit("passControl", ((client_id, client_proposal),))

        elif isinstance(m, BrickCallInstanceMessage):
            try:
                timestamp = m.getTimestamp()
                brick_name = m.getBrickName()
                widget_name = m.getWidgetName()
                widget_method = m.getWidgetMethod()
                widget_method_args = m.getWidgetMethodArgs()
                brick = self.guiConfiguration.findItem(brick_name).brick

                if widget_name == "":
                    exec("method=brick.%s" % widget_method)
                else:
                    exec("method=brick.%s.%s" % (widget_name, widget_method))
                self.emit("widgetCall", (timestamp, method, widget_method_args))
            except Exception:
                logging.getLogger("HWR").exception(
                    "InstanceServer: problem while calling a brick!"
                )

        elif isinstance(m, BrickUpdateInstanceMessage):
            try:
                timestamp = m.getTimestamp()
                brick_name = m.getBrickName()
                widget_name = m.getWidgetName()
                widget_method = m.getWidgetMethod()
                widget_method_args = m.getWidgetMethodArgs()
                masterSync = m.getMasterSync()

                # if necessary check this with Qt3 version
                brick = self.guiConfiguration.findItem(brick_name).get("brick")

                if widget_name == "":
                    exec("method=brick.%s" % widget_method)
                else:
                    exec("method=brick.%s.%s" % (widget_name, widget_method))
                self.emit(
                    "widgetUpdate", (timestamp, method, widget_method_args, masterSync)
                )
            except Exception:
                logging.getLogger("HWR").exception(
                    "InstanceServer: problem while updating a brick!"
                )

        elif isinstance(m, TabUpdateInstanceMessage):
            try:
                timestamp = m.getTimestamp()
                tab_name = m.getTabName()
                tab_index = m.getTabIndex()
                tab = self.guiConfiguration.findItem(tab_name).widget

                method = tab.setCurrentPage
                method_args = (tab_index,)
                self.emit("widgetUpdate", (timestamp, method, method_args))
            except Exception:
                logging.getLogger("HWR").exception(
                    "InstanceServer: problem while updating a tab!"
                )

    def serverMessageReceived(self, client_addr, data):
        m = self.parseReceivedMessage(data)
        if m is None:
            return

        if isinstance(m, NewClientInstanceMessage):
            try:
                client_new_id = m.getClientNewId()
            except KeyError:
                new_proposal = m.getNewProposal()
                # print "SERVER NEWCLIENT PROPOSAL",new_proposal,self.clients

                found_id = None
                for cli_id in self.clients:
                    cli_addr = self.clients[cli_id][0]
                    if cli_addr == client_addr:
                        found_id = cli_id
                        cli_prop = self.clients[cli_id][1]
                        msg = NewClientInstanceMessage()
                        msg.setClientId(cli_id)
                        msg.setProposal(cli_prop)
                        msg.setNewProposal(new_proposal)
                        msg.setAvailable(True)
                        data = msg.encode()
                        broadcast_to_clients(data)
                        self.emit(
                            "clientChanged",
                            ((cli_id, cli_prop), (cli_id, new_proposal)),
                        )
                        break

                if found_id is not None:
                    if self.controlId2[0] == found_id:
                        self.controlId2[1] = new_proposal
                    self.clients[cli_id][1] = new_proposal

            else:

                try:
                    count = self.idCount[client_new_id]
                except KeyError:
                    self.idCount[client_new_id] = 1
                else:
                    count += 1
                    self.idCount[client_new_id] = count
                    client_new_id = "%s-%d" % (client_new_id, count)
                    self.idCount[client_new_id] = 1

                found_id = None
                for cli_id in self.clients:
                    cli_addr = self.clients[cli_id][0]
                    if cli_addr == client_addr:
                        found_id = cli_id
                        cli_prop = self.clients[cli_id][1]
                        msg = NewClientInstanceMessage()
                        msg.setClientId(cli_id)
                        msg.setClientNewId(client_new_id)
                        msg.setProposal(cli_prop)
                        msg.setAvailable(True)
                        data = msg.encode()
                        broadcast_to_clients(data)
                        self.emit(
                            "clientChanged",
                            ((cli_id, cli_prop), (client_new_id, cli_prop)),
                        )
                        break

                if found_id is not None:
                    if self.controlId2[0] == found_id:
                        self.controlId2[0] = client_new_id
                    self.clients[client_new_id] = self.clients[found_id]
                    self.clients.pop(found_id)

        elif isinstance(m, AskPermissionInstanceMessage):
            client_id = m.getClientId()
            client_proposal = m.getProposal()

            try:
                count = self.idCount[client_id]
            except KeyError:
                self.idCount[client_id] = 1
            else:
                count += 1
                self.idCount[client_id] = count
                client_id = "%s-%d" % (client_id, count)
                self.idCount[client_id] = 1

            self.clients[client_id] = [client_addr, client_proposal]

            msg = NewClientInstanceMessage()
            msg.setClientId(client_id)
            msg.setProposal(client_proposal)
            msg.setAvailable(True)
            data = msg.encode()
            broadcast_to_clients(data, avoid=(client_addr,))

            for cli_id in self.clients:
                if cli_id != client_id:
                    msg = NewClientInstanceMessage()
                    cli_addr = self.clients[cli_id][0]
                    cli_prop = self.clients[cli_id][1]
                    msg.setClientId(cli_id)
                    msg.setProposal(cli_prop)
                    msg.setAvailable(True)
                    data = msg.encode()
                    send_data_to_client(client_addr, data)

            self.synchronizeClientWithEvents(client_addr)

            msg = GivePermissionInstanceMessage()
            msg.setClientId(client_id)
            msg.setServerId(self.serverId2[0])
            msg.setProposal(self.serverId2[1])
            data = msg.encode()
            send_data_to_client(client_addr, data)

            msg = PassControlInstanceMessage()
            msg.setClientId(self.controlId2[0])
            msg.setProposal(self.controlId2[1])
            data = msg.encode()
            send_data_to_client(client_addr, data)

            self.emit("newClient", ((client_id, client_proposal),))

        elif isinstance(m, ChatInstanceMessage):
            found_id = None

            for cli_id in self.clients:
                cli_addr = self.clients[cli_id][0]
                if cli_addr == client_addr:
                    found_id = cli_id
                    found_prop = self.clients[cli_id][1]
            if found_id is not None:
                m.setChatNick(found_id)
                m.setProposal(found_prop)
                data = m.encode()
                broadcast_to_clients(data, avoid=(client_addr,))
                self.emit(
                    "chatMessageReceived",
                    (m.getChatPriority(), (found_id, found_prop), m.getChatMessage()),
                )

        elif isinstance(m, AskControlInstanceMessage):
            found_id = None
            found_prop = None
            for cli_id in self.clients:
                cli_addr = self.clients[cli_id][0]
                if cli_addr == client_addr:
                    found_id = cli_id
                    found_prop = self.clients[cli_id][1]

            if found_id is not None:
                m.setClientId(found_id)
                if found_prop is not None:
                    m.setProposal(found_prop)
                data = m.encode()
                broadcast_to_clients(data)

                self.emit("wantsControl", ((found_id, found_prop),))

        elif isinstance(m, PassControlInstanceMessage):
            client_id = m.getClientId()
            if self.serverId2[0] == client_id:
                self.takeControl()
            else:
                try:
                    cli_addr = self.clients[client_id][0]
                except KeyError:
                    pass
                else:
                    client_prop = self.clients[client_id][1]

                    msg = ControlInstanceMessage()
                    msg.setHasControl(False)
                    data = msg.encode()
                    send_data_to_client(client_addr, data)

                    msg = PassControlInstanceMessage()
                    msg.setClientId(client_id)
                    msg.setProposal(client_prop)
                    data = msg.encode()
                    broadcast_to_clients(data, avoid=(cli_addr,))

                    self.controlId2 = [client_id, client_prop]
                    self.emit("passControl", ((client_id, client_prop),))

                    msg = ControlInstanceMessage()
                    msg.setHasControl(True)
                    data = msg.encode()
                    send_data_to_client(cli_addr, data)

        elif isinstance(m, BrickCallInstanceMessage):
            try:
                timestamp = m.getTimestamp()
                brick_name = m.getBrickName()
                widget_name = m.getWidgetName()
                widget_method = m.getWidgetMethod()
                widget_method_args = m.getWidgetMethodArgs()
                brick = self.guiConfiguration.findItem(brick_name).brick

                if widget_name == "":
                    exec("method=brick.%s" % widget_method)
                else:
                    exec("method=brick.%s.%s" % (widget_name, widget_method))
                self.emit("widgetCall", (timestamp, method, widget_method_args))
            except Exception:
                logging.getLogger("HWR").exception(
                    "InstanceServer: problem while calling a brick!"
                )

        elif isinstance(m, BrickUpdateInstanceMessage):
            broadcast_to_clients(data, avoid=(client_addr,))

            try:
                timestamp = m.getTimestamp()
                brick_name = m.getBrickName()
                widget_name = m.getWidgetName()
                widget_method = m.getWidgetMethod()
                widget_method_args = m.getWidgetMethodArgs()
                brick = self.guiConfiguration.findItem(brick_name).brick
                masterSync = m.getMasterSync()
                if widget_name == "":
                    exec("method=brick.%s" % widget_method)
                else:
                    exec("method=brick.%s.%s" % (widget_name, widget_method))
                self.emit(
                    "widgetUpdate", (timestamp, method, widget_method_args, masterSync)
                )
            except Exception:
                logging.getLogger("HWR").exception(
                    "InstanceServer: problem while updating a brick!"
                )

        elif isinstance(m, TabUpdateInstanceMessage):
            broadcast_to_clients(data, avoid=(client_addr,))

            try:
                timestamp = m.getTimestamp()
                tab_name = m.getTabName()
                tab_index = m.getTabIndex()
                tab = self.guiConfiguration.findItem(tab_name).widget

                method = tab.setCurrentPage
                method_args = (tab_index,)
                self.emit("widgetUpdate", (timestamp, method, method_args))
            except Exception:
                logging.getLogger("HWR").exception(
                    "InstanceServer: problem while updating a tab!"
                )

        elif isinstance(m, TakeControlInstanceMessage):
            found_id = None
            found_prop = None
            for cli_id in self.clients:
                cli_addr = self.clients[cli_id][0]
                if cli_addr == client_addr:
                    found_id = cli_id
                    found_prop = self.clients[cli_id][1]

            if found_id is not None:
                if self.controlId2[0] == self.serverId2[0]:
                    self.emit("haveControl", (False,))
                else:
                    control_addr = self.clients[self.controlId2[0]][0]
                    msg = ControlInstanceMessage()
                    msg.setHasControl(False)
                    data = msg.encode()
                    send_data_to_client(control_addr, data)

                msg = PassControlInstanceMessage()
                msg.setClientId(found_id)
                msg.setProposal(found_prop)
                data = msg.encode()
                broadcast_to_clients(data)

                self.controlId2 = [found_id, found_prop]
                self.emit("passControl", ((found_id, found_prop),))

                msg = ControlInstanceMessage()
                msg.setHasControl(True)
                data = msg.encode()
                send_data_to_client(cli_addr, data)


def handleRemoteClient(client_socket, addr):
    SERVER_CLIENTS[addr] = client_socket
    INSTANCE_HO.clientConnected(addr, client_socket)

    buffer = ""
    while True:
        data = client_socket.recv(1024)
        if data == "":
            try:
                SERVER_CLIENTS.pop(addr)
            except Exception:
                # Huh? socket closed but client is not in SERVER_CLIENTS dict!
                # just ignore silently
                pass
            else:
                INSTANCE_HO.clientClosed(addr)
            break
        buffer += data
        msgs = buffer.split(TERMINATOR)
        buffer = msgs.pop()
        for msg in msgs:
            INSTANCE_HO.serverMessageReceived(addr, msg)


def broadcast_to_clients(data, avoid=None):
    for client_addr in list(SERVER_CLIENTS.keys()):
        if avoid and client_addr in avoid:
            continue
        send_data_to_client(client_addr, data)


def send_data_to_client(client_addr, data):
    client_socket = SERVER_CLIENTS.get(client_addr)
    if client_socket:
        try:
            client_socket.sendall("%s%s" % (data, TERMINATOR))
        except Exception:
            # broken pipe? client disconnected
            SERVER_CLIENTS.pop(client_addr)


def InstanceClient(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((host, port))
    except Exception:
        raise
    else:
        socketName = s.getsockname()

    def handle_incoming_data(client_socket):
        buffer = ""
        while True:
            data = client_socket.recv(1024)
            if data == "":
                INSTANCE_HO.serverClosed()
                break
            buffer += data
            msgs = buffer.split(TERMINATOR)
            buffer = msgs.pop()
            for msg in msgs:
                INSTANCE_HO.clientMessageReceived(msg)

    CLIENTS[socketName] = s
    gevent.spawn(handle_incoming_data, s)

    return socketName


def send_data_to_server(socket_name, data):
    client_socket = CLIENTS[socket_name]
    client_socket.sendall("%s%s" % (data, TERMINATOR))


class InstanceMessage:
    (
        TYPE_CHAT,
        TYPE_CONTROL,
        TYPE_NEWCLIENT,
        TYPE_ASKPERMISSION,
        TYPE_GIVEPERMISSION,
        TYPE_ASKCONTROL,
        TYPE_PASSCONTROL,
        TYPE_BRICKUPDATE,
        TYPE_TABUPDATE,
        TYPE_TAKECONTROL,
        TYPE_BRICKCALL,
    ) = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10)

    def __init__(self, data=None):
        self.messageDict = {}
        if data is not None:
            self.messageDict = pickle.loads(data)

    def encode(self):
        try:
            self.messageDict["type"]
        except KeyError:
            raise ValueError
        return pickle.dumps(self.messageDict)

    def getType(self):
        try:
            t = self.messageDict["type"]
        except KeyError:
            raise ValueError
        return t


class ChatInstanceMessage(InstanceMessage):
    (PRIORITY_LOW, PRIORITY_NORMAL, PRIORITY_HIGH) = (0, 1, 2)

    def __init__(self, instance_message=None):
        InstanceMessage.__init__(self)
        if instance_message is not None:
            self.messageDict = instance_message.messageDict
        self.messageDict["type"] = InstanceMessage.TYPE_CHAT

    def setChatMessage(self, priority, message):
        self.messageDict["priority"] = priority
        self.messageDict["message"] = message

    def setChatNick(self, nick):
        self.messageDict["nick"] = nick

    def getChatMessage(self):
        return self.messageDict["message"]

    def getChatPriority(self):
        return self.messageDict["priority"]

    def getChatNick(self):
        return self.messageDict["nick"]

    def setProposal(self, proposal):
        self.messageDict["proposal"] = proposal

    def getProposal(self):
        return self.messageDict["proposal"]


class ControlInstanceMessage(InstanceMessage):
    def __init__(self, instance_message=None):
        InstanceMessage.__init__(self)
        if instance_message is not None:
            self.messageDict = instance_message.messageDict
        self.messageDict["type"] = InstanceMessage.TYPE_CONTROL

    def setHasControl(self, has_control):
        self.messageDict["control"] = has_control

    def getHasControl(self):
        return self.messageDict["control"]


class PassControlInstanceMessage(InstanceMessage):
    def __init__(self, instance_message=None):
        InstanceMessage.__init__(self)
        if instance_message is not None:
            self.messageDict = instance_message.messageDict
        self.messageDict["type"] = InstanceMessage.TYPE_PASSCONTROL

    def setClientId(self, client_id):
        self.messageDict["client_id"] = client_id

    def getClientId(self):
        return self.messageDict["client_id"]

    def setProposal(self, proposal):
        self.messageDict["proposal"] = proposal

    def getProposal(self):
        return self.messageDict["proposal"]


class AskControlInstanceMessage(InstanceMessage):
    def __init__(self, instance_message=None):
        InstanceMessage.__init__(self)
        if instance_message is not None:
            self.messageDict = instance_message.messageDict
        self.messageDict["type"] = InstanceMessage.TYPE_ASKCONTROL

    def setClientId(self, client_id):
        self.messageDict["client_id"] = client_id

    def getClientId(self):
        return self.messageDict["client_id"]

    def setProposal(self, proposal):
        self.messageDict["proposal"] = proposal

    def getProposal(self):
        return self.messageDict["proposal"]


class AskPermissionInstanceMessage(InstanceMessage):
    def __init__(self, instance_message=None):
        InstanceMessage.__init__(self)
        if instance_message is not None:
            self.messageDict = instance_message.messageDict
        self.messageDict["type"] = InstanceMessage.TYPE_ASKPERMISSION

    def setClientId(self, client_id):
        self.messageDict["client_id"] = client_id

    def getClientId(self):
        return self.messageDict["client_id"]

    def setProposal(self, proposal):
        self.messageDict["proposal"] = proposal

    def getProposal(self):
        return self.messageDict["proposal"]


class GivePermissionInstanceMessage(InstanceMessage):
    def __init__(self, instance_message=None):
        InstanceMessage.__init__(self)
        if instance_message is not None:
            self.messageDict = instance_message.messageDict
        self.messageDict["type"] = InstanceMessage.TYPE_GIVEPERMISSION

    def setClientId(self, client_id):
        self.messageDict["client_id"] = client_id

    def getClientId(self):
        return self.messageDict["client_id"]

    def setServerId(self, server_id):
        self.messageDict["server_id"] = server_id

    def getServerId(self):
        return self.messageDict["server_id"]

    def setProposal(self, proposal):
        self.messageDict["proposal"] = proposal

    def getProposal(self):
        return self.messageDict["proposal"]


class NewClientInstanceMessage(InstanceMessage):
    def __init__(self, instance_message=None):
        InstanceMessage.__init__(self)
        if instance_message is not None:
            self.messageDict = instance_message.messageDict
        self.messageDict["type"] = InstanceMessage.TYPE_NEWCLIENT

    def setClientId(self, client_id):
        self.messageDict["client_id"] = client_id

    def getClientId(self):
        return self.messageDict["client_id"]

    def setClientNewId(self, client_new_id):
        self.messageDict["client_new_id"] = client_new_id

    def getClientNewId(self):
        return self.messageDict["client_new_id"]

    def setAvailable(self, available):
        self.messageDict["available"] = available

    def getAvailable(self):
        return self.messageDict["available"]

    def setProposal(self, proposal):
        self.messageDict["proposal"] = proposal

    def getProposal(self):
        return self.messageDict["proposal"]

    def setNewProposal(self, proposal):
        self.messageDict["new_proposal"] = proposal

    def getNewProposal(self):
        return self.messageDict["new_proposal"]


class BrickUpdateInstanceMessage(InstanceMessage):
    def __init__(self, instance_message=None):
        InstanceMessage.__init__(self)
        if instance_message is not None:
            self.messageDict = instance_message.messageDict
        self.messageDict["type"] = InstanceMessage.TYPE_BRICKUPDATE

    def setBrickUpdate(
        self,
        brick_name,
        widget_name,
        widget_method,
        widget_method_args,
        masterSync=True,
    ):
        self.messageDict["timestamp"] = time.time()
        self.messageDict["brick_name"] = brick_name
        self.messageDict["widget_name"] = widget_name
        self.messageDict["widget_method"] = widget_method
        self.messageDict["widget_method_args"] = widget_method_args
        self.messageDict["masterSync"] = masterSync

    def getTimestamp(self):
        return self.messageDict["timestamp"]

    def getBrickName(self):
        return self.messageDict["brick_name"]

    def getWidgetName(self):
        return self.messageDict["widget_name"]

    def getWidgetMethod(self):
        return self.messageDict["widget_method"]

    def getWidgetMethodArgs(self):
        return self.messageDict["widget_method_args"]

    def getMasterSync(self):
        return self.messageDict["masterSync"]


class TabUpdateInstanceMessage(InstanceMessage):
    def __init__(self, instance_message=None):
        InstanceMessage.__init__(self)
        if instance_message is not None:
            self.messageDict = instance_message.messageDict
        self.messageDict["type"] = InstanceMessage.TYPE_TABUPDATE

    def setTabUpdate(self, tab_name, tab_index):
        self.messageDict["timestamp"] = time.time()
        self.messageDict["tab_name"] = tab_name
        self.messageDict["tab_index"] = tab_index

    def getTimestamp(self):
        return self.messageDict["timestamp"]

    def getTabName(self):
        return self.messageDict["tab_name"]

    def getTabIndex(self):
        return self.messageDict["tab_index"]


class TakeControlInstanceMessage(InstanceMessage):
    def __init__(self, instance_message=None):
        InstanceMessage.__init__(self)
        if instance_message is not None:
            self.messageDict = instance_message.messageDict
        self.messageDict["type"] = InstanceMessage.TYPE_TAKECONTROL


class BrickCallInstanceMessage(BrickUpdateInstanceMessage):
    def __init__(self, instance_message=None):
        InstanceMessage.__init__(self)
        if instance_message is not None:
            self.messageDict = instance_message.messageDict
        self.messageDict["type"] = InstanceMessage.TYPE_BRICKCALL
