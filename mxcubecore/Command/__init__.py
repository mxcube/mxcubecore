"""Command package

The Command package is the place to put command launchers
and channel readers/writers modules.

The modules should be organised by control software, i.e.
in the 'Spec' module you will find the SpecCommand and
SpecChannel classes.

Command launchers and channels should derive from the
CObject class of the HardwareRepository.CommandContainer module.
They should emit the following Qt signals :
- connected, when connected to the control software
- disconnected, when disconnected from control software
and implement the isConnected() method.

Every command launcher class in the module should emit
the following Qt signals :
- commandBeginWaitReply, when the command has been sent
and we are waiting for the reply. The only argument
is the command 'user' name. Useful for setting up a
message to the user. *SHOULD NOT BLOCK EXECUTION*
- commandReplyArrived, when the reply for the command
is arrived. The arguments are: reply value and command
'user' name.
- commandFailed, when the command failed to execute.
The arguments are: error message and command 'user' name.
- commandAborted, when the command has been aborted.
The arguments are: command 'user' name.

Every command launcher should be a callable object ; the
arguments provided are those for the remote command to
be executed.

A Channel object should emit the following signals :
- 'update', when the value of the channel changes

A channel object should have a 'get_value' method at least,
and an optional 'setValue'
"""
