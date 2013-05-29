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

import logging
import os
import pprint

from turnstile import middleware

from train import util


LOG = logging.getLogger(__name__)


class Response(object):
    """
    Accumulates a response from an application.  The status code will
    be in the ``status`` attribute, the headers will be normalized
    (upper-case, with dashes converted to underscores) and represented
    as a dictionary in the ``headers`` attribute, and the response
    body will be stored in the ``body`` attribute.
    """

    def __init__(self):
        """
        Initialize a ``Response`` object.
        """

        self.status = None
        self.headers = {}
        self.body = ''

    def __call__(self, application, environ):
        """
        Call the given application with the designated WSGI
        environment.  Returns the ``Response`` object.

        :param application: A WSGI application.
        :param environ: The WSGI environment for the request.
        """

        # Call the application and consume its response
        result = application(environ, self.start_response)
        for data in result:
            if data:
                self.body += str(data)

    def start_response(self, status, response_headers, exc_info=None):
        """
        The ``start_response`` callable passed as part of the WSGI
        specification.  No attempt is made to enforce the required
        behavior; i.e., this version of ``start_response`` may be
        called multiple times without error.

        :param status: The status code.
        :param response_headers: A list of tuples designating the
                                 response headers and their values.
        :param exc_info: Exception information that may be passed by
                         the application.  Ignored.

        :returns: Returns the ``write()`` method for compliance with
                  the WSGI specification.
        """

        self.status = status
        self.headers.update((k.upper().replace('-', '_'), v)
                            for k, v in response_headers)
        return self.write

    def write(self, data):
        """
        The ``write`` callable returned by ``start_response()``.
        Calling this method is deprecated, but this is supported by
        the WSGI specification for backwards compatibility.

        :param data: Data to be included in the response body.
        """

        if data:
            self.body += str(data)


class TrainServer(object):
    """
    Represents the fake server used to feed requests through the
    Turnstile filter.  Since the filter expects to be called with
    another WSGI callable, this class also implements a fake
    application which returns "200 OK" with an "X-Train-Server" header
    (value "completed").  The body of the fake response will be the
    pretty-printed WSGI environment dictionary.
    """

    def __init__(self, filter):
        """
        Initialize the ``TrainServer`` object.

        :param filter: The Turnstile filter callable.
        """

        self.application = filter(self.fake_app)

    def __call__(self, environ):
        """
        Process a request.

        :param environ: The request, represented as a WSGI environment
                        dictionary.  Turnstile will be called to
                        process the request.

        :returns: A ``Response`` instance.
        """

        response = Response()
        response(self.application, environ)
        return response

    def fake_app(self, environ, start_response):
        """
        Fake WSGI application.  Since Turnstile is a filter, it needs
        the next application in the pipeline to function properly;
        this method acts as that fake application.  It returns a "200
        OK" response, with the "X-Train-Server" header set to
        "completed".  The input environment will be pretty-printed and
        returned as the body of the response.

        :param environ: The request environment.
        :param start_response: A callable for starting the response.

        :returns: A list of one element: the pretty-printed request
                  environment.
        """

        start_response('200 OK', [('x-train-server', 'completed')])
        return [pprint.pformat(environ)]

    def start(self, queue):
        """
        Read requests from the queue, process them, and log the
        results.

        :param queue: A queue object, implementing ``get()``.
        """

        # Get our PID for logging purposes
        pid = os.getpid()

        while True:
            environ = queue.get()

            # Log the request
            LOG.info("%d: Processing request %s" %
                     (pid, pprint.pformat(environ)))

            # Process the request
            response = self(environ)

            # Log the response
            LOG.info("%d: Response code %r; headers %s; body %r" %
                     (pid, response.status,
                      pprint.pformat(response.headers), response.body))

    @classmethod
    def from_confitems(cls, items):
        """
        Construct a ``TrainServer`` object from the configuration
        items.

        :param items: A list of ``(key, value)`` tuples describing the
                      configuration to feed to the Turnstile middleware.

        :returns: An instance of ``TrainServer``.
        """

        local_conf = dict(items)
        filter = middleware.turnstile_filter({}, **local_conf)
        return cls(filter)


def start_workers(queue, items, workers=1):
    """
    Start the train workers.  Each worker pops requests off the queue,
    passes them through Turnstile, and logs the result.

    :param queue: A queue object, implementing ``get()``.
    :param items: A list of ``(key, value)`` tuples describing the
                  configuration to feed to the Turnstile middleware.
    :param workers: The number of workers to create.

    :returns: A list of process IDs of the workers.
    """

    # Generate the server object
    train_server = TrainServer.from_confitems(items)
    launcher = util.Launcher(train_server.start, queue)

    servers = []
    for worker in range(workers):
        # Launch the server
        servers.append(launcher.start())

    return servers
