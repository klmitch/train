# Copyright 2013 Rackspace
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import __builtin__
import ConfigParser
import logging
import logging.config
import multiprocessing
import os
import signal
import sys
import time

import cli_tools


@cli_tools.argument("config",
                    action="store",
                    help="Configuration for Train (and Turnstile).")
@cli_tools.argument("requests",
                    action="store",
                    nargs='*',
                    help="Files describing the requests to feed through "
                    "Turnstile.")
@cli_tools.argument("--workers", "-w",
                    action="store",
                    type=int,
                    help="Number of workers to use.  Default is drawn from "
                    "the configuration file, or 1 if none is provided.")
@cli_tools.argument("--log-config", "-l",
                    action="store",
                    help="Name of a logging configuration.  Default is drawn "
                    "from the configuration file, if one is provided.")
def train(config, requests=None, workers=1, log_config=None):
    """
    Run the Train benchmark tool.

    :param config: The name of the configuration file to read.
    :param requests: A list of one or more request files to read.
    :param workers: The number of workers to use.
    :param log_config: The name of a logging configuration file.
    """

    # If we're using nova_limits, that relies on _ being declared,
    # which is presumably done by nova-api.  We need to dummy it out
    # so that this works...
    __builtin__._ = lambda x: x  # Pragma: nocover

    # Read in the configuration
    conf = ConfigParser.SafeConfigParser()
    conf.read([config])

    # We must have a Turnstile section
    if not conf.has_section('turnstile'):
        raise Exception("No Turnstile configuration available")

    # Which log configuration do we use?
    if not log_config:
        # Try to get it from the configuration
        try:
            log_config = conf.get('train', 'log_config')
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            pass

    # Try to configure from a file, if one is specified
    if log_config:
        try:
            # Try to read configuration from a file
            logging.config.fileConfig(log_config)
        except Exception as exc:
            print >>sys.stderr, ("Warning: Failed to read logging "
                                 "configuration from file %r: %s" %
                                 (log_config, exc))
            log_config = None

    # OK, last-ditch logging configuration
    if not log_config:
        logging.basicConfig()

    # Now that logging has been configured, we can import other train
    # modules; this has to wait until now, because each starts off
    # with a "LOG = logging.getLogger(__name__)", and that logger will
    # not reflect the configuration that was set up above
    from train import request
    from train import wsgi

    # Determine the number of workers to employ
    if not workers:
        # Try to get it from the configuration
        try:
            workers = int(conf.get('train', 'workers'))
        except (ValueError, ConfigParser.NoSectionError,
                ConfigParser.NoOptionError):
            # Default to 1
            workers = 1

    # Add any requests files from configuration
    if not requests:
        requests = []
    try:
        requests += conf.get('train', 'requests').split()
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        pass

    # Demand we have some requests files, too
    if not requests:
        raise Exception("No requests to feed through Turnstile")

    # Now, we need the sequences
    sequences = request.parse_files(requests)

    # Set up the queue
    queue = multiprocessing.Queue()

    # Start the workers
    servers = wsgi.start_workers(queue, conf.items('turnstile'), workers)

    # And now we start feeding in the requests
    procs = []
    for seq in sequences:
        proc = multiprocessing.Process(target=seq.queue_request, args=(queue,))
        proc.start()
        procs.append(proc)

    # Wait for all the sequence feeders to shut down, which they'll do
    # as soon as they've finished submitting all the requests
    for proc in procs:
        proc.join()

    # Ask all the servers to exit, nicely
    for server in servers:
        queue.put('STOP')

    # The sequence processes will not actually exit until all items
    # fed by them into the queue have been pulled off.  Thus, the
    # queue should be empty...but let's be sure
    while not queue.empty():
        time.sleep(1)

    # Now let's give the processes a little time to finish doing their
    # thing...
    time.sleep(1)

    # OK, now make sure *all* the drivers exit
    for server in servers:
        try:
            os.kill(server, signal.SIGTERM)
        except OSError:
            # That server's already stopped
            pass
