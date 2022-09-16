#!/usr/bin/env python

# SPDX-FileCopyrightText: 2021 S. Vijay Kartik <vijay.kartik@desy.de>, DESY
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Utility functions for internal use by online analysis triggering modules at different beamlines.

Functions
---------

get_beamtime_metadata():
    Load all beamtime metadata required to access remote computing resources.

locate_metadata_file():
    Guess the location of the metadata file for current beamtime.

parse_metadata_file():
    Read metadata file located at the root of every beamtime directory.
    Get information about online analysis, like temporary account name, credentials, slurm reservations etc.

map_local_to_remote_path(beamline_local_path, cluster_rootdir, cluster_subdir):
    Generate file path on the remote cluster corresponding to a local file path as shown at the beamline.

name_resultfile_with_suffix(datafile_path, result_suffix):
    Generate full file path on local beamline filesystem, derived from input data file.

name_resultdir(datafile_path):
    Get the full path of the location to store results corresponding to the input data file.

make_writable_dir(dir_name):
    Create a directory and make it world-writable, world-readable.

run_subprocess():
    Run command either on local machine with Bash, or after connecting to remote machine with SSH
"""

from __future__ import print_function
import sys
import os
import glob  # To find the beamtime metadata file
import yaml  # To parse the beamtime metadata file
import subprocess


assert sys.version_info >= (2, 7), 'Python version too old'  # If Python version < 2.7 no point going further

if sys.version_info >= (3, 6):
    from enum import IntEnum, auto, unique

    @unique
    class TriggerMethod(IntEnum):
        """
        Supported triggering methods.
        """
        SLURM_REST_API = auto()
        REMOTE_SBATCH_SCRIPT = auto()
        LOCAL_BASH_SCRIPT = auto()
else:  # 2.7 < version < 3.6, because enum only appeared in 3.4, auto() in 3.6
    class TriggerMethod:
        """
        Stop-gap enum solution for older Python versions
        """
        SLURM_REST_API = 0
        REMOTE_SBATCH_SCRIPT = 1
        LOCAL_BASH_SCRIPT = 2


class Trigger:
    """
    Collective information needed to trigger an online analysis run.

    Information about access to remote online computing resources
    """
    def __init__(self, trigger_method=TriggerMethod.REMOTE_SBATCH_SCRIPT, beamline_root_dir='/gpfs'):
        """
        Construct a Trigger object with relevant information for remote computing resource access.

        :param trigger_method: method to use for triggering processing, either locally or remotely
        :param beamline_root_dir: full path to root directory of beamline filesystem
        """
        self.trigger_method = trigger_method  # TODO: make this data member immutable from this point on
        self.beamtime_metadata_file = locate_metadata_file(beamline_root_dir)
        self.beamline, self.beamtime, self.remote_data_dir, self.user_name, self.user_sshkey, \
            self.slurm_reservation, self.slurm_partition, self.slurm_node = parse_metadata_file(self.beamtime_metadata_file)
        # Results are written to the _beamline filesystem through a mountpoint on reserved cluster nodes
        beamlinefs_mountpoint = os.path.join('/beamline', self.beamline)  # TODO: Hardcoded mountpoint, current location as per IT
        beamlinefs_currdir = self.get_beamtime_tag()  # either 'current' or <commissioning id>
        self.remote_result_dir = os.path.join(beamlinefs_mountpoint, beamlinefs_currdir)

    def get_beamtime_tag(self):
        """
        Get tag for current beamtime.

        :returns: 'current' for regular user beamtimes, <commissioning ID> for commissioning beamtimes
        """
        curr_beamtime_dir = os.path.dirname(self.beamtime_metadata_file)
        return os.path.basename(curr_beamtime_dir.rstrip('/'))  # either 'current' or <commissioning id>

    def get_ssh_command(self):
        """
        Prepare SSH command to be run on the local node, including all options for accessing remote computing resources.

        Put together temporary online analysis user, access keys, and job submission node in one SSH call.

        :returns: prepared SSH command with all required options for remote connections
        """
        # I think str.format() needs explicit positional arguments {0}, {1} instead of {} {} in Python versions < 3.1
        ssh_command = '/usr/bin/ssh'
        ssh_opts_general = "-o BatchMode=yes -o CheckHostIP=no -o StrictHostKeyChecking=no -o GSSAPIAuthentication=no -o GSSAPIDelegateCredentials=no -o PasswordAuthentication=no -o PubkeyAuthentication=yes -o PreferredAuthentications=publickey -o ConnectTimeout=10"
        ssh_opts_user = '-l {0}'.format(self.user_name)
        ssh_opts_key = '-i {0}'.format(self.user_sshkey)
        ssh_opts_host = self.slurm_node
        ssh_command += ' {0} {1} {2} {3}'.format(ssh_opts_general, ssh_opts_key, ssh_opts_user, ssh_opts_host)  # Leading space in arguments important!
        return ssh_command

    def get_sbatch_command(self, jobname_prefix='onlineanalysis', job_dependency='singleton', logfile_path='/dev/null'):
        """
        Prepare Slurm sbatch command to be run on the remote node, including all Slurm reservation parameters.

        :param jobname_prefix: label to prefix to all Slurm jobs for identification
        :param job_dependency: Slurm job dependency, to influence job queue handling (and better utilize CPU/Memory)
        :param logfile_path: **DEPRECATED** full path to logfile
        :returns: prepared sbatch command with all required options for job submission
        """
        # TODO: Taking logfile path temporarily, but this is ugly.
        # TODO: Remove function parameter here, make the analysis program log its output in a file independent of sbatch
        sbatch_command = '/usr/bin/sbatch'
        sbatch_opts_jobname = '{0}_{1.beamline}_{1.beamtime}'.format(jobname_prefix, self)
        sbatch_opts_dependency = job_dependency  # only run one sbatch job (with same user+jobname) at a time
        sbatch_opts_logfile = logfile_path
        # sbatch_opts = '--partition={} --reservation={} --job-name={} --dependency={} --output={}'.format(self.analyse_trigger.slurm_partition, self.analyse_trigger.slurm_reservation, sbatch_opts_jobname, sbatch_opts_dependency, logfilepath_cluster)
        
        #Old version, removed singleton option
        #sbatch_opts = '--partition={0.slurm_partition} --reservation={0.slurm_reservation} --job-name={1} --dependency={2} --output={3}'.format(
        #    self, sbatch_opts_jobname, sbatch_opts_dependency, sbatch_opts_logfile)

        sbatch_opts = '--partition={0.slurm_partition} --reservation={0.slurm_reservation} --job-name={1} --output={2}'.format(
            self, sbatch_opts_jobname, sbatch_opts_logfile)
        

        
        
        
        #sbatch_opts = '--partition={0.slurm_partition} --reservation={0.slurm_reservation} --job-name={1}'.format(
        #    self, sbatch_opts_jobname)
        
        
        
        sbatch_command += ' {0}'.format(sbatch_opts)
        return sbatch_command

    def run(self, arg_list=[]):
        """
        Function to trigger processing on remote nodes.

        :param arg_list: argument list, empty for trigger methods through REST APIs,
                         otherwise containing script file path and script arguments for trigger methods
                         through local slurm or remote sbatch scripts
        :returns: None
        """
        if self.trigger_method is TriggerMethod.LOCAL_BASH_SCRIPT:
            if not arg_list:
                raise RuntimeError('Bash script not provided')
            script_file = retrieve_script_path(arg_list)
            script_args = retrieve_arg_list(arg_list)
            if not os.path.exists(script_file):  # TODO: Check if script_file is executable
                if sys.version_info < (3, 4):
                    raise OSError('File not found: {}'.format(script_file))
                raise FileNotFoundError('File not found: {}'.format(script_file))
            run_subprocess([script_file] + script_args)
        elif self.trigger_method is TriggerMethod.REMOTE_SBATCH_SCRIPT:
            if not arg_list:
                raise RuntimeError('Sbatch script not provided')
            script_file = retrieve_script_path(arg_list)
            script_args = retrieve_arg_list(arg_list)
            ssh_command = self.get_ssh_command()
            sbatch_command = self.get_sbatch_command()
            # The command to run looks like this: ssh -o options hostname "sbatch sbatchoptions sbatchfile sbatchargs" &
            # The last entry in the argument list is to finish the command to run on the remote node, and push the SSH call to the background
            run_subprocess([ssh_command, '"{0} {1}'.format(sbatch_command, script_file)] + script_args + ['" &'])
            # TODO: Check if & is needed when using subprocess.Popen with start_new_session=True
        elif self.trigger_method is TriggerMethod.SLURM_REST_API:
            raise RuntimeError('Slurm REST API not available')
        else:
            raise RuntimeError('Trigger method not known')


def locate_metadata_file(root_dir='/gpfs'):
    """
    Get the path to the metadata JSON file for the current beamtime

    This function only works in the online situation where there is a currently
    running beamtime.

    :param root_dir: top directory of beamline
    :returns: full path to metadata JSON file provided for the current beamtime
    """
    # root_dir is, AFAIK, always '/gpfs' at PETRA III
    # /gpfs/local is always present, we want to ignore it. Normally there should only be either a /gpfs/current, or /gpfs/<commisioning id> subdirectory
    # The metadata file should be located directly in this subdirectory
    try:
        beamtime_dirs = [
            path
            for path in [
                os.path.join(root_dir, entry)
                for entry in os.listdir(root_dir)]
            if os.path.isdir(path) and not path.endswith('local')]
    except OSError as e:  # if root_dir does not exist
        print(e)
        if sys.version_info < (3, 4):
            raise OSError('Root directory does not exist: ' + str(root_dir))
        raise FileNotFoundError('Root directory does not exist: ' + str(root_dir))
    metadata_files = []
    for curr_dir in beamtime_dirs + [root_dir]:  # also check root_dir, in case the root directory contains a metadata file (e..g when root_dir = '/gpfs/current')
        curr_dir_metadata_files = glob.glob('{0}/*metadata*.json'.format(curr_dir))
        metadata_files.extend(curr_dir_metadata_files)  # if there happens to be more than one directory with a metadata json file - which is BAD
    if len(metadata_files) is not 1:  # also handles the case where no metadata file is found
        if sys.version_info < (3, 4):
            raise OSError('Unique metadata JSON file not found')
        raise FileNotFoundError('Unique metadata JSON file not found')
    return metadata_files[0]


def parse_metadata_file(metadatafile_path):
    """
    Parse beamtime metadata file to get information relevant to current beamtime and online analysis.

    :param metadatafile_path: full path to metadata file
    :returns: tuple containing variables relevant for online analysis
    """
    # DESY-IT has switched to a fully valid JSON file for the beamtime metadata file (since 2020.06.12).
    beamline = ''  # String containing beamline name
    beamtime = ''  # String containing beamtime or commissioning run ID
    coredatadir = ''  # Path to directory where data is stored on the Core filesystem
    temp_user_name = ''  # Username for temporary account allotted for online analysis on Maxwell
    temp_user_sshkeyfile = ''  # Path to private SSH key for the temp account
    slurm_reservation = ''  # Name of slurm reservation (changes between pre-start and start)
    slurm_partition = ''  # Name of slurm partition
    reserved_nodes = []  # List of allocated slurm node(s)
    with open(metadatafile_path, 'r') as mdfile:
        try:
            md = yaml.safe_load(mdfile)  # Modern YAML parsers can also load pure JSON
            if 'beamline' in md:
                beamline = str(md['beamline'])
            if 'beamtimeId' in md:  # For user run
                beamtime = str(md['beamtimeId'])
            elif 'id' in md:  # For commissioning run
                beamtime = str(md['id'])
            if 'corePath' in md:
                coredatadir = str(md['corePath'])
            if 'onlineAnalysis' in md:  # extra parameters only available when beamtime started with --pre-start to allocate online analysis resources
                temp_user_name = str(md['onlineAnalysis']['userAccount'])
                temp_user_sshkeyfile = str(md['onlineAnalysis']['sshPrivateKeyPath'])
                slurm_reservation = str(md['onlineAnalysis']['slurmReservation'])
                slurm_partition = str(md['onlineAnalysis']['slurmPartition'])
                reserved_nodes = md['onlineAnalysis']['reservedNodes']
        except:  # TODO: Don't use bare except
            raise RuntimeError('JSON parsing of metadata file failed', metadatafile_path)

    if not beamline:
        raise RuntimeError('Beamline ID not found', metadatafile_path)
    if not beamtime:
        raise RuntimeError('Beamtime ID not found', metadatafile_path)
    if not coredatadir:
        raise RuntimeError('Data location on remote filesystem unknown', metadatafile_path)
    if not temp_user_name:
        raise RuntimeError('Temporary account for online analysis unknown ', metadatafile_path)
    if not temp_user_sshkeyfile:
        raise RuntimeError('SSH key for online analysis account not found', metadatafile_path)
    if not slurm_reservation:
        raise RuntimeError('Slurm reservation for online analysis not found', metadatafile_path)
    if not slurm_partition:
        raise RuntimeError('Slurm partition for online analysis not found', metadatafile_path)
    if not reserved_nodes:
        raise RuntimeError('Reserved node(s) for online analysis not found', metadatafile_path)
    else:
        temp_user_sshkeyfile = os.path.join(os.path.dirname(metadatafile_path), temp_user_sshkeyfile)
        slurm_node = str(reserved_nodes[0])  # The first reserved node will do just fine as a Slurm job submission node

    return beamline, beamtime, coredatadir, temp_user_name, temp_user_sshkeyfile, slurm_reservation, slurm_partition, slurm_node


def get_beamtime_metadata(root_dir='/gpfs'):
    """
    Convenience function to load partial beamtime metadata relevant for online analysis.

    Automatically finds a metadata file and parses it for information required for online analysis.

    :param root_dir: top directory for beamtime
    :returns: tuple containing 'relevant' metadata for later use in online analysis
    """
    metadata_file = locate_metadata_file(root_dir)
    return parse_metadata_file(metadata_file)


def map_local_to_remote_path(beamline_local_path, cluster_rootdir, cluster_subdir):
    """
    Generate file path on the remote cluster corresponding to a local file path as shown at the beamline.

    This generates the right path, for files either in the core filesystem, or a mountpoint for the
    beamline filesystem present on a Maxwell node.

    :param beamline_local_path: full path of a file as seen at the beamline
    :param cluster_rootdir: full path of the root directory for the file in the cluster (core-fs for data, beamline mountpoint for results)
    :param cluster_subdir: subdirectory name, 'raw' for data files, 'processed' for result and log files
    :returns: full path to the file, valid on the remote cluster
    """
    beamline_rootdir, beamline_filepath = beamline_local_path.split(cluster_subdir, 1)
    return os.path.join(cluster_rootdir, cluster_subdir.lstrip('/'), beamline_filepath.lstrip('/'))


def name_resultfile_with_suffix(datafile_path, result_suffix):
    """
    Construct name of a result file, derived from the input data file name.

    :param datafile_path: full path to data file
    :param result_suffix: suffix to use to generate result filename
    :returns: name of result file (Note: not the full path). The file is not guaranteed to exist at this point.
    """
    result_filename_base, result_filename_ext = os.path.splitext(os.path.basename(datafile_path))
    if not result_filename_base or not result_filename_ext:
        raise RuntimeError('File name in unexpected form')

    return result_filename_base + result_suffix + result_filename_ext


def name_resultdir(datafile_path):
    """
    Get the full path of the directory to store result files corresponding to the input data file.

    :param datafile_path: full path to data file
    :returns: full path to results directory. The directory is not guaranteed to exist at this point.
    """
    bl_rootdir, bl_datafile_path = datafile_path.split('raw', 1)
    # TODO: Is it good to have a hard-coded name for the result top directory: 'processed/onlineanalysis' ?
    return os.path.join(bl_rootdir, 'processed', 'onlineanalysis', os.path.dirname(bl_datafile_path.lstrip('/')))


def make_writable_dir(dir_name):
    """
    Create a directory and make it world-writable, world-readable.

    :param dir_name: path to directory to be created
    :returns: None
    """
    if not os.path.exists(dir_name):  # Python >= 3.2 call to os.makedirs() takes optional argument 'exists_ok' which makes this current check unnecessary
        # os.makedirs(dir_name, mode=0o777, exist_ok=True)  # Default mode of leaf directory is supposed to 0o77, but it may be ignored, depending on the umask. Set the mode explicitly later
        os.makedirs(dir_name)  # Default mode of leaf directory is supposed to 0o77, but it may be ignored, depending on the umask. Set the mode explicitly to be sure
        os.chmod(dir_name, 0o777)  # In case the results directory is created with permissions that forbid the beamtime account from writing to it. Tests show this does indeed happen, and is probably due to the umask inherited from the Macroserver executing the onlineanalysis module functions


def run_subprocess(arg_list):
    """
    Use Python's subprocess module to run a command with arguments.

    :param arg_list: list comprising the command (+ arguments) to be run
    :returns: None
    """
    flattened_arg_list = list(flatten_arg_list(arg_list))  # In case there are lists inside arg_list, and not just 'plain' entries
    stringified_arg_list = [str(entry) for entry in flattened_arg_list]  # No input sanitization done here
    try:
        if sys.version_info >= (3, 3):  # subprocess.DEVNULL appears in 3.3, start_new_session in 3.2
            subprocess.Popen(stringified_arg_list, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)  # Needs Python 3.3+
        elif sys.version_info >= (2, 7):
            with open(os.devnull, 'w') as DEVNULL:
                subprocess.Popen(stringified_arg_list, stdout=DEVNULL, stderr=DEVNULL, preexec_fn=os.setsid)  # Works in Python 2.7, can potentially deadlock if many threads in application
        else:
            print('Python version too old. No process run.', file=sys.stderr)
    except ValueError as e:
        print(e, file=sys.stderr)
        print('Did not trigger analysis - invalid args to subprocess.Popen()', file=sys.stderr)
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        print('Did not trigger analysis - no trigger script found', file=sys.stderr)
    except OSError as e:
        print(e, file=sys.stderr)
        print('Did not trigger analysis', file=sys.stderr)
    except IOError as e:
        print(e, file=sys.stderr)
        print('Did not trigger analysis', file=sys.stderr)


def run_slurm():
    """
    Use Slurm REST API to submit a batch job directly from the local machine.
    :returns: None
    """
    raise RuntimeError('No implementation exists')


def retrieve_script_path(arg_list):
    """
    Internal function.

    Extract path to script file from the argument list arg_list provided to Trigger.run.
    The script file is expected to appear first in the argument list.

    :param arg_list: list containing script file path and script arguments
    :returns: path to script file, given as first entry in the argument list
    """
    # TODO: This doesn't account for script file names which include spaces!
    # arg_list can look like one of these (empty lists not expected):
    # 1. ['script_file']
    # 2. ['script_file arg1 arg2 ... argN']
    # 3. ['script_file', [arg1, arg2, ..., argN]]
    # 4. ['script_file', arg1, arg2, ..., argN]
    if not arg_list:
        raise RuntimeError('Empty list input not supported')
    script_file = str(arg_list[0]).split(None, 1)[0]

    return script_file


def retrieve_arg_list(arg_list):
    """
    Internal function.

    Extract list of arguments for the script also given in the argument list arg_list provided to Trigger.run.

    :param arg_list: list containing script file path and script arguments
    :returns: list of arguments to be forwarded to the script
    """
    # TODO: This doesn't account for script file names which include spaces!
    # arg_list can look like one of these (empty lists not expected):
    # 1. ['script_file']
    # 2. ['script_file arg1 arg2 ... argN']
    # 3. ['script_file', [arg1, arg2, ..., argN]]
    # 4. ['script_file', arg1, arg2, ..., argN]
    if not arg_list:
        raise RuntimeError('Empty list input not supported')
    if len(arg_list) == 1:  # Cases 1. and 2.
        if arg_list[0] == retrieve_script_path(arg_list):  # Case 1.
            script_args = []
        else:  # Case 2.
            script_args = str(arg_list[0]).split()[1:]  # BEWARE!! Wrong if script_file has spaces
    elif len(arg_list) == 2 and isinstance(arg_list[0], str) and isinstance(arg_list[1], list):  # Case 3, probably most commonly occurring
        script_args = arg_list[1]
    else:  # Case 4.
        script_args = arg_list[1:]

    return script_args


def flatten_arg_list(arg_list):
    """
    Internal function.

    Flattens any internal lists present in arg_list.

    :param arg_list: a list containing 'scalar' entries and list entries
    :returns: a flattened list only containing 'scalar' (i.e., non-list) entries
    """
    for maybe_list in arg_list:
        if isinstance(maybe_list, list) and not isinstance(maybe_list, str):  # May not work for non-latin encodings
            for sub_list in flatten_arg_list(maybe_list):
                yield sub_list
        else:
            yield maybe_list

