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

import StringIO
import sys
import urllib

from train import util


class RequestParseException(Exception):
    """
    Raised when an exception occurs parsing a request file.
    """

    pass


class Sequence(object):
    """
    Represent a sequence of requests.
    """

    def __init__(self, name, global_headers):
        """
        Initialize a ``Sequence`` object.

        :param name: The name of the sequence.

        :param global_headers: A dictionary of headers at the global
                               scope.
        """

        self.name = name
        self.headers = util.StackedDict(global_headers)
        self.requests = []

    def push(self, req):
        """
        Push a new request onto the ``Sequence``.

        :param req: The request to push onto the ``Sequence``.  May
                    also be an instance of ``Gap``.
        """

        self.requests.append(req)


class Request(object):
    """
    Represent a request within a sequence.  This will contain the
    method, URL, and full header set.  It will implement a function
    that will generate a WSGI environment dictionary.
    """

    def __init__(self, sequence, method, uri):
        """
        Initialize a ``Request`` object.

        :param sequence: The ``Sequence`` object of which this request
                         is a member.
        :param method: The HTTP method.
        :param uri: The URI to be requested.
        """

        self.method = method.upper()
        self.uri = uri
        self.headers = util.StackedDict(sequence.headers)

    def fix(self):
        """
        Fixate the headers on the request.  This converts the headers
        ``StackedDict`` object into a plain dictionary.
        """

        self.headers = self.headers.copy()

    def synthesize(self):
        """
        Synthesize the WSGI environment dictionary, based on the
        request.

        :returns: A dictionary containing the WSGI dictionary.
        """

        path_info = self.uri.split('?', 1)

        environ = {
            'wsgi.input': StringIO.StringIO(''),
            'wsgi.errors': sys.stderr,
            'wsgi.version': (1, 0),
            'wsgi.multithread': True,
            'wsgi.multiprocess': False,
            'wsgi.run_once': False,
            'wsgi.url_scheme': 'http',
            'REQUEST_METHOD': self.method,
            'SCRIPT_NAME': '',
            'RAW_PATH_INFO': path_info[0],
            'PATH_INFO': urllib.unquote(path_info[0]),
            'SERVER_PROTOCOL': 'HTTP/1.0',
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '80',
            'REMOTE_ADDR': 'localhost',
            'REMOTE_PORT': '80',
            'GATEWAY_INTERFACE': 'CGI/1.1',
        }

        # Add the query string
        if len(path_info) > 1:
            environ['QUERY_STRING'] = path_info[1]

        # Determine the content type
        if 'CONTENT_TYPE' in self.headers:
            ctype = self.headers['CONTENT_TYPE'].partition(';')[0].strip()
            environ['CONTENT_TYPE'] = ctype
        else:
            environ['CONTENT_TYPE'] = 'text/plain'

        # Determine the content length
        if 'CONTENT_LENGTH' in self.headers:
            environ['CONTENT_LENGTH'] = self.headers['CONTENT_LENGTH']

        # Add all the headers
        for name, value in self.headers.items():
            environ['HTTP_' + name] = value

        return environ


class Gap(object):
    """
    Represent a time gap in a request sequence file.
    """

    def __init__(self, delta):
        """
        Initialize a ``Gap`` instance.

        :param delta: The time delta to insert before the next request
                      is generated.
        """

        self.delta = delta


class PartialHeader(object):
    """
    Represent a header being built.  This is used by the parser to
    allow for headers that are split across multiple lines.
    """

    @staticmethod
    def canon_name(name):
        """
        Canonicalize a header name.

        :param name: The name to canonicalize.

        :returns: The name, converted to uppercase and with all dashes
                  converted to underscores.
        """

        return name.upper().replace('-', '_')

    def __init__(self, name, value):
        """
        Initialize a ``PartialHeader`` instance.

        :param name: The name of the header.
        :param value: The partial value for the header.
        """

        # Canonicalize the header name to uppercase with dashes
        # replaced by underscores; this makes creating the WSGI
        # environment later a little easier
        self.name = self.canon_name(name)

        # Canonicalize the whitespace in the value
        self.value = ' '.join(value.split())

    def __iadd__(self, other):
        """
        Add text to the value of this partial header.

        :param other: The text to add.

        :returns: Returns this ``PartialHeader`` object.
        """

        # Canonicalize whitespace in other and join to the preceding
        # value with a single space
        self.value += ' ' + ' '.join(other.split())

        return self


class RequestParseState(object):
    """
    Represent the state of parsing a request file.
    """

    def __init__(self):
        """
        Initialize a ``RequestParseState`` object.
        """

        # Base of the headers tree; this contains globally-set headers
        self._headers = util.StackedDict()

        # Keep a dictionary of sequences being built
        self._sequences = {}

        # The current sequence
        self._sequence = None

        # The current request
        self._request = None

        # The header currently being built
        self._header = None

    def start_sequence(self, fname, name):
        """
        Signal the start of a section with the given name.  A section
        with no name switches back to the global scope.

        :param fname: The name of the file being parsed.
        :param name: The name of the section.
        """

        # Apply partial headers
        if self._header:
            self.finish_header(fname)

        # Apply partial request
        if self._request:
            self.finish_request(fname)

        # Determine which scope to go to
        if name:
            # It's a sequence; look it up or create it
            if name not in self._sequences:
                self._sequences[name] = Sequence(name, self._headers)
            self._sequence = self._sequences[name]
        else:
            # Back to global scope
            self._sequence = None

    def start_request(self, fname, method, uri):
        """
        Signal the start of a request with the given method and URI.

        :param fname: The name of the file being parsed.
        :param method: The HTTP method.
        :param uri: The URI to be requested.
        """

        # Ensure we're called from the correct state
        if not self._sequence:
            raise RequestParseException("Request outside of a sequence "
                                        "while reading file %s" % fname)

        # Apply partial headers
        if self._header:
            self.finish_header(fname)

        # Apply partial request
        if self._request:
            self.finish_request(fname)

        # Set up the new request
        self._request = Request(self._sequence, method, uri)

        # Go ahead and add it to the sequence
        self._sequence.push(self._request)

    def finish_request(self, fname):
        """
        Finish the processing of a request.

        :param fname: The name of the file being parsed.
        """

        # Fixate the request headers
        self._request.fix()

        # Clear the partial request
        self._request = None

    def push_gap(self, fname, delta):
        """
        Insert a gap into the request sequence.

        :param fname: The name of the file being parsed.
        :param delta: The time delta to insert before the next request
                      is generated.
        """

        # Ensure we're called from the correct state
        if not self._sequence:
            raise RequestParseException("Gap outside of a sequence while "
                                        "reading file %s" % fname)

        # Apply partial headers
        if self._header:
            self.finish_header(fname)

        # Apply partial request
        if self._request:
            self.finish_request(fname)

        # Push the gap onto the sequence
        self._sequence.push(Gap(delta))

    def start_header(self, fname, name, value):
        """
        Start processing a header.  Headers may be continued on the
        next line.

        :param fname: The name of the file being parsed.
        :param name: The name of the header.
        :param value: The partial value for the header.
        """

        # Apply partial headers
        if self._header:
            self.finish_header(fname)

        # Prepare the partial header
        self._header = PartialHeader(name, value)

    def extend_header(self, fname, value):
        """
        Add more to the value of a header.

        :param fname: The name of the file being parsed.
        :param value: The partial value to add to the header.
        """

        # Ensure we're called from the correct state
        if not self._header:
            raise RequestParseException("Header continuation without a "
                                        "header while reading file %s" %
                                        fname)

        self._header += value

    def finish_header(self, fname):
        """
        Finish the processing of a header.

        :param fname: The name of the file being parsed.
        """

        # Apply the header to the headers object
        self.headers[self._header.name] = self._header.value

        # Clear the partial header
        self._header = None

    def delete_header(self, fname, name):
        """
        Delete a header.

        :param fname: The name of the file being parsed.
        :param name: The name of the header to delete.
        """

        # Apply partial headers
        if self._header:
            self.finish_header(fname)

        # Delete the header
        try:
            del self.headers[PartialHeader.canon_name(name)]
        except KeyError:
            pass

    def reset_header(self, fname, name):
        """
        Reset a header.  This restores the header to what it was in
        the parent environment.

        :param fname: The name of the file being parsed.
        :param name: The name of the header to reset.
        """

        # Apply partial headers
        if self._header:
            self.finish_header(fname)

        # Reset the header
        self.headers.reset(PartialHeader.canon_name(name))

    def finish(self, fname):
        """
        Called when processing of the request file is complete.
        Ensures that all partial processing is completed.

        :param fname: The name of the file being parsed.
        """

        # Apply partial headers
        if self._header:
            self.finish_header(fname)

        # Apply partial request
        if self._request:
            self.finish_request(fname)

        # Reset all state; this allows the state object to be reused
        self._sequence = None
        self._request = None
        self._header = None

        # Reset global headers for the next file
        self._headers.reset()

        # Hit the headers on all the sequences
        for seq in self._sequences.values():
            seq.headers.reset()

    @property
    def sequences(self):
        """
        Retrieve a list of all sequences.
        """

        return self._sequences.values()

    @property
    def headers(self):
        """
        Retrieve the headers currently being manipulated.
        """

        if self._request:
            return self._request.headers
        if self._sequence:
            return self._sequence.headers
        return self._headers


def _parse_file(state, fname):
    """
    Perform the processing of a request file.

    :param state: A ``RequestParseState`` object containing the parser
                  state.
    :param fname: The name of the request file.
    """

    with open(fname) as f:
        for line in f:
            # Ignore comment lines
            if line[:1] == '#':
                continue

            # Now strip out in-line comments...
            for idx, char in enumerate(line):
                # idx is guaranteed to be > 1 here because we've
                # handled the case of '#' in column 0 above
                if char == '#' and line[idx - 1].isspace():
                    line = line[:idx]
                    break

            # We're going to strip the line, but let's check for
            # leading space, indicating a header continuation
            header = line[:1].isspace()
            line = line.strip()

            # If the line is empty after stripping it, let's skip it
            if not line:
                continue

            # Now let's see what we've got...
            if header:
                # It was a header continuation...
                state.extend_header(fname, line)
                continue
            elif line[0] == '[':
                # We have a sequence marker
                if line[-1] != ']':
                    raise RequestParseException("Invalid sequence header %r "
                                                "while reading file %s" %
                                                (line, fname))
                state.start_sequence(fname, line[1:-1].strip())
                continue
            elif line[0] == '+':
                # We have a message gap
                try:
                    state.push_gap(fname, float(line[1:]))
                except ValueError:
                    raise RequestParseException("Invalid gap value %r "
                                                "while reading file %s" %
                                                (line[1:], fname))
                continue  # Pragma: nocover
            elif line[0] == '-':
                # We have a delete header request
                state.delete_header(fname, line[1:].strip())
                continue
            elif line[0] == '!':
                # We have a reset header request
                state.reset_header(fname, line[1:].strip())
                continue

            # OK, it's either a request or a header...
            for idx, char in enumerate(line):
                if char.isspace():
                    # We have a request!
                    state.start_request(fname, line[:idx], line[idx:].strip())
                    break
                elif char == ':':
                    # We have a header!
                    state.start_header(fname, line[:idx],
                                       line[idx + 1:].strip())
                    break
            else:
                raise RequestParseException("Unable to parse line %r "
                                            "while reading file %s" %
                                            (line, fname))

    # Finished processing this file
    state.finish(fname)


def parse_files(fnames):
    """
    Parses a list of request files.

    :param fnames: A list of file names to parse.

    :returns: A list of the sequences that were loaded from the files.
    """

    state = RequestParseState()

    for fname in fnames:
        _parse_file(state, fname)

    return state.sequences
