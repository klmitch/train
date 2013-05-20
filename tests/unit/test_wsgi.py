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

    @mock.patch('os.getpid', return_value=1234)
    @mock.patch.object(wsgi, 'LOG')
    @mock.patch.object(wsgi.TrainServer, '__call__', return_value=mock.Mock(
        status='200 OK',
        headers=dict(X_TEST='test header'),
        body='response body here',
    ))
    def test_start(self, mock_call, mock_LOG, mock_getpid):
        filter = mock.Mock(return_value='filter')
        ts = wsgi.TrainServer(filter)
        environs = [dict(request='0'), dict(request='1'), TestException]
        queue = mock.Mock(**{'get.side_effect': environs})

        self.assertRaises(TestException, ts.start, queue)

        queue.assert_has_calls([
            mock.call.get(),
            mock.call.get(),
            mock.call.get(),
        ])
        mock_LOG.assert_has_calls([
            mock.call.notice("1234: Processing request {'request': '0'}"),
            mock.call.notice("1234: Response code '200 OK'; headers "
                             "{'X_TEST': 'test header'}; body "
                             "'response body here'"),
            mock.call.notice("1234: Processing request {'request': '1'}"),
            mock.call.notice("1234: Response code '200 OK'; headers "
                             "{'X_TEST': 'test header'}; body "
                             "'response body here'"),
        ])
        mock_call.assert_has_calls([
            mock.call(dict(request='0')),
            mock.call(dict(request='1')),
        ])

    @mock.patch('turnstile.middleware.turnstile_filter',
                return_value=mock.Mock(return_value='filter'))
    def test_from_confitems(self, mock_turnstile_filter):
        items = [('item1', 'value 1'), ('item2', 'value 2')]

        result = wsgi.TrainServer.from_confitems(items)

        self.assertEqual(result.application, 'filter')
        mock_turnstile_filter.assert_called_once_with(
            {}, item1='value 1', item2='value 2')
        mock_turnstile_filter.return_value.assert_called_once_with(
            result.fake_app)


class TestStartWorkers(unittest2.TestCase):
    @mock.patch.object(wsgi.TrainServer, 'from_confitems',
                       return_value=mock.Mock(start='starter'))
    @mock.patch('train.util.Launcher', return_value=mock.Mock(**{
        'start.return_value': 'worker_pid',
    }))
    def test_one_worker(self, mock_Launcher, mock_from_confitems):
        result = wsgi.start_workers('queue', 'items')

        self.assertEqual(result, ['worker_pid'])
        mock_from_confitems.assert_called_once_with('items')
        mock_Launcher.assert_called_once_with('starter', 'queue')
        mock_Launcher.return_value.start.assert_called_once_with()

    @mock.patch.object(wsgi.TrainServer, 'from_confitems',
                       return_value=mock.Mock(start='starter'))
    @mock.patch('train.util.Launcher', return_value=mock.Mock(**{
        'start.return_value': 'worker_pid',
    }))
    def test_five_workers(self, mock_Launcher, mock_from_confitems):
        result = wsgi.start_workers('queue', 'items', 5)

        self.assertEqual(result, ['worker_pid'] * 5)
        mock_from_confitems.assert_called_once_with('items')
        mock_Launcher.assert_called_once_with('starter', 'queue')
        mock_Launcher.return_value.start.assert_has_calls([
            mock.call(),
            mock.call(),
            mock.call(),
            mock.call(),
            mock.call(),
        ])
