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

import ConfigParser
import multiprocessing
import os
import signal
import time

import cli_tools

from train import request
from train import wsgi


@cli_tools.argument("config",
                    action="store",
                    help="Configuration for Train (and Turnstile).")
@cli_tools.argument("requests",
                    action="append",
                    nargs='*',
                    help="Files describing the requests to feed through "
                    "Turnstile.")
@cli_tools.argument("--workers", "-w",
                    action="store",
                    type=int,
                    help="Number of workers to use.  Default is drawn from "
                    "the configuration file, or 1 if none is provided.")
def train(config, requests=None, workers=1):
    """
    Run the Train benchmark tool.

    :param config: The name of the configuration file to read.
    :param requests: A list of one or more request files to read.
    :param workers: The number of workers to use.
    """

    # Read in the configuration
    conf = ConfigParser.SafeConfigParser()
    conf.read([config])

    # We must have a Turnstile section
    if not conf.has_section('turnstile'):
        raise Exception("No Turnstile configuration available")

    # Determine the number of workers to employ
    if workers is None:
        # Try to get it from the configuration
        try:
            workers = int(conf.get('train', 'workers'))
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            # Default to 1
            workers = 1

    # Add any requests files from configuration
    if not requests:
        requests = []
    try:
        requests += conf.get('train', 'requests').split()
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        pass

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

    # The sequence processes will not actually exit until all items
    # fed by them into the queue have been pulled off.  Thus, the
    # queue should be empty...but let's be sure
    while not queue.empty():
        time.sleep(1)

    # OK, now let's kill all the turnstile drivers
    for server in servers:
        os.kill(server, signal.SIGTERM)
