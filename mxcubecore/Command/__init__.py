"""Command package.

The Command package is the place to put Command launchers
and Channel readers/writers modules.

The modules are organised by Control System Software used at different facilities 
or specific to the hardware targeted.
Not all the facilities or even different beamlines from a facility have the same dependencies installed.
**One should modify the** ``pyproject.toml`` **to address their needs.**

CommandObject class and ChannelObject class derive from the mxcubecore.CommandContainer module.
They should both emit the following signals :
    - ``connected``, when connected to the control software
    - ``disconnected``, when disconnected from control software
They should both implement the ``is_connected()`` method.

    - Command launcher class in the module should emit the following signals :
        - ``commandBeginWaitReply``, when the command has been sent and we are waiting for the reply.
     
        - ``commandReplyArrived``, when the reply for the commandis arrived.

        - ``commandFailed``, when the command failed to execute.

        - ``commandAborted``, when the command has been aborted.
 
Every Command launcher should be a callable object ;
the arguments provided are those for the remote command to
be executed.

    - A Channel object should:
        - have a ``get_value`` method
        - have a ``set_value`` method (optional)
        - emit an ``update`` signal when the value of the channel changes
"""
