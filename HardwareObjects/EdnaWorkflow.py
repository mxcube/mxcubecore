from HardwareRepository.BaseHardwareObjects import Device
import logging
from lxml import etree
import types

class EdnaWorkflow(Device):
    
    def __init__(self, name):
        Device.__init__(self, name)

    def init(self):
        logging.getLogger('HWR').debug('%r initializing', self)
        self.state = self.getChannelObject('state')
        self.state.connectSignal('update', self.state_changed)
        logging.getLogger('HWR').debug('got state channel %r with value %r', self.state, self.state.value)

        self.current_actor = self.getChannelObject('current_actor')
        self.current_actor.connectSignal('update', self.current_actor_changed)

        self.start_command = self.getCommandObject('start')
        self.start_command.connectSignal('commandFailed', self.set_command_failed)

        self.abort_command = self.getCommandObject('abort')
        self.abort_command.connectSignal('commandFailed', self.set_command_failed)
        
        self.get_parameters_command = self.getCommandObject('get_parameters')
        self.get_values_map_command = self.getCommandObject('get_values_map')
        self.set_values_map_command = self.getCommandObject('set_values_map')
        self.get_available_workflows_command = self.getCommandObject('get_available_workflows')
        self._command_failed = False
        
    def command_failure(self):
        return self._command_failed
    
    def set_command_failed(self, *args):
        logging.getLogger("HWR").error("Workflow '%s' Tango command failed!" % args[1])
        self._command_failed = True
        
    def state_changed(self, new_value):
        new_value = str(new_value)
        logging.getLogger("HWR").debug('%s: state changed to %r', str(self.name()), new_value)
        self.emit('stateChanged', (new_value, ))
        if new_value == "OPEN":
            params = self.get_parameters()
            self.emit('parametersNeeded', (params, ))
            
    def current_actor_changed(self, new_value):
        logging.getLogger('HWR').debug('%s: current actor changed to %r', str(self.name()), new_value)
        self.emit('currentActorChanged', (new_value, ))

    def get_parameters(self):
        params = None
        try:
            params = self.get_parameters_command()
        except:
            logging.getLogger("HWR").error('%s: could not read parameters', str(self.name()))
        finally:
            return params
    
    def get_values_map(self):
        # the server sends the map in the format:
        # [key,value,key2,value2,...]
        
        params_dict = dict()
        try:
            params = self.get_values_map_command()
            for i in range(0, len(params), 2):
                params_dict[params[i]] = params[i+1]
        except:
            logging.getLogger("HWR").error('%s: could not read values map', str(self.name()))
        finally:
            return params_dict

    def set_values_map(self, params):
        # params is a dict and we want to send a [key,value, ...] flat list
        params_list = list()
        for (k,v) in params.iteritems():
            params_list.append(k)
            params_list.append(v)
            
        try:
            self.set_values_map_command(params_list)
        except:
            logging.getLogger("HWR").error('%s: could not set values map', str(self.name()))

    def get_available_workflows(self):
        workflows = list()
        try:
            wfxml = self.get_available_workflows_command()
            if type(wfxml) == types.ListType and len(wfxml) > 0:
                wfxml = wfxml[0]
            logging.debug('workflow list from the server:\n%r', wfxml)
        except:
            logging.getLogger("HWR").exception('%s: could not get the list of available workflows', str(self.name()))
            return workflows

        # extract the infos in a list of dicts    
        parsed = etree.fromstring(wfxml)
        root = parsed#.getroot()
        for child in root.iterchildren():
            wfdict = dict()
            if child.tag != 'workflow':
                logging.warning('removing malformed wf entry %r (bad tag)', child)
                continue
            for subtag in child.iterchildren():
                wfdict[subtag.tag] = subtag.text.strip()
            # ensure we have all we need
            if all([wfdict.has_key(x) for x in ['name', 'doc', 'path']]):
                workflows.append(wfdict)
            else:
                logging.warning('removed malformed wf entry %r (missing one of name, doc or path subtags)', child)
        return workflows

    def abort(self):
        logging.getLogger("HWR").info('Aborting current workflow')
        self._command_failed = False
        self.abort_command()
        
    def start(self, workflow):
        self._command_failed = False
        self.start_command(workflow)
        
