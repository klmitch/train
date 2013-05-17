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

import mock
import unittest2

from train import wsgi


class TestResponse(unittest2.TestCase):
    def test_init(self):
        resp = wsgi.Response()

        self.assertEqual(resp.status, None)
        self.assertEqual(resp.headers, {})
        self.assertEqual(resp.body, '')

    def test_call(self):
        application = mock.Mock(return_value=['body 0\n', '', 'body 1\n', 8])
        resp = wsgi.Response()

        resp(application, 'environ')

        application.assert_called_once_with('environ', resp.start_response)
        self.assertEqual(resp.body, 'body 0\nbody 1\n8')

    def test_start_response(self):
        resp = wsgi.Response()

        result = resp.start_response('200 OK', [
            ('header-1', 'value 1'),
            ('header-2', 'value 2'),
        ])

        self.assertEqual(result, resp.write)
        self.assertEqual(resp.status, '200 OK')
        self.assertEqual(resp.headers, {
            'HEADER_1': 'value 1',
            'HEADER_2': 'value 2',
        })

    def test_write_empty(self):
        resp = wsgi.Response()
        resp.body = 'prefix:'

        resp.write('')

        self.assertEqual(resp.body, 'prefix:')

    def test_write_nonstr(self):
        resp = wsgi.Response()
        resp.body = 'prefix:'

        resp.write(23)

        self.assertEqual(resp.body, 'prefix:23')

    def test_write_str(self):
        resp = wsgi.Response()
        resp.body = 'prefix:'

        resp.write("some body text")

        self.assertEqual(resp.body, 'prefix:some body text')


class TestException(Exception):
    pass


class TestTrainServer(unittest2.TestCase):
    def test_init(self):
        filter = mock.Mock(return_value='filter')

        ts = wsgi.TrainServer(filter)

        filter.assert_called_once_with(ts.fake_app)
        self.assertEqual(ts.application, 'filter')

    @mock.patch.object(wsgi, 'Response', return_value=mock.Mock())
    def test_call(self, mock_Response):
        filter = mock.Mock(return_value='filter')
        ts = wsgi.TrainServer(filter)

        result = ts('environ')

        self.assertEqual(result, mock_Response.return_value)
        mock_Response.assert_called_once_with()
        mock_Response.return_value.assert_called_once_with('filter', 'environ')

    @mock.patch('pprint.pformat', return_value="[pretty dict]")
    def test_fake_app(self, mock_pformat):
        filter = mock.Mock(return_value='filter')
        ts = wsgi.TrainServer(filter)
        start_response = mock.Mock()

        result = ts.fake_app('environ', start_response)

        self.assertEqual(result, ["[pretty dict]"])
        start_response.assert_called_once_with(
            '200 OK', [('x-train-server', 'completed')])
        mock_pformat.assert_called_once_with('environ')
