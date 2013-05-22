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
import signal
import StringIO
import sys

import mock
import unittest2

from train import runner


class TestTrain(unittest2.TestCase):
    def setup_conf(self, **kwargs):
        def fake_has_section(sect):
            return sect in kwargs

        def fake_get(sect, opt):
            if sect not in kwargs:
                raise ConfigParser.NoSectionError(sect)
            elif opt not in kwargs[sect]:
                raise ConfigParser.NoOptionError(opt, sect)

            return kwargs[sect][opt]

        def fake_items(sect):
            if sect not in kwargs:
                raise ConfigParser.NoSectionError(sect)

            return kwargs[sect].items()

        return mock.Mock(**{
            'has_section.side_effect': fake_has_section,
            'get.side_effect': fake_get,
            'items.side_effect': fake_items,
        })

    @mock.patch.object(sys, 'stderr', StringIO.StringIO())
    @mock.patch.object(ConfigParser, 'SafeConfigParser')
    @mock.patch('logging.basicConfig')
    @mock.patch('logging.config.fileConfig')
    @mock.patch('multiprocessing.Process')
    @mock.patch('multiprocessing.Queue')
    @mock.patch('os.kill')
    @mock.patch('time.sleep')
    @mock.patch('train.request.parse_files')
    @mock.patch('train.wsgi.start_workers')
    def test_missing_config(self, mock_start_workers, mock_parse_files,
                            mock_sleep, mock_kill, mock_Queue, mock_Process,
                            mock_fileConfig, mock_basicConfig,
                            mock_SafeConfigParser):
        conf = self.setup_conf()
        mock_SafeConfigParser.return_value = conf

        self.assertRaises(Exception, runner.train, 'train.cfg')

        mock_SafeConfigParser.assert_called_once_with()
        conf.assert_has_calls([
            mock.call.read(['train.cfg']),
            mock.call.has_section('turnstile'),
        ])
        self.assertEqual(len(conf.method_calls), 2)
        self.assertFalse(mock_fileConfig.called)
        self.assertFalse(mock_basicConfig.called)
        self.assertFalse(mock_parse_files.called)
        self.assertFalse(mock_Queue.called)
        self.assertFalse(mock_start_workers.called)
        self.assertFalse(mock_Process.called)
        self.assertFalse(mock_sleep.called)
        self.assertFalse(mock_kill.called)
        self.assertEqual(sys.stderr.getvalue(), '')

    @mock.patch.object(sys, 'stderr', StringIO.StringIO())
    @mock.patch.object(ConfigParser, 'SafeConfigParser')
    @mock.patch('logging.basicConfig')
    @mock.patch('logging.config.fileConfig')
    @mock.patch('multiprocessing.Process')
    @mock.patch('multiprocessing.Queue')
    @mock.patch('os.kill')
    @mock.patch('time.sleep')
    @mock.patch('train.request.parse_files')
    @mock.patch('train.wsgi.start_workers')
    def test_missing_requests(self, mock_start_workers, mock_parse_files,
                              mock_sleep, mock_kill, mock_Queue, mock_Process,
                              mock_fileConfig, mock_basicConfig,
                              mock_SafeConfigParser):
        conf = self.setup_conf(turnstile={})
        mock_SafeConfigParser.return_value = conf

        self.assertRaises(Exception, runner.train, 'train.cfg')

        mock_SafeConfigParser.assert_called_once_with()
        conf.assert_has_calls([
            mock.call.read(['train.cfg']),
            mock.call.has_section('turnstile'),
            mock.call.get('train', 'log_config'),
            mock.call.get('train', 'requests'),
        ])
        self.assertEqual(len(conf.method_calls), 4)
        self.assertFalse(mock_fileConfig.called)
        mock_basicConfig.assert_called_once_with()
        self.assertFalse(mock_parse_files.called)
        self.assertFalse(mock_Queue.called)
        self.assertFalse(mock_start_workers.called)
        self.assertFalse(mock_Process.called)
        self.assertFalse(mock_sleep.called)
        self.assertFalse(mock_kill.called)
        self.assertEqual(sys.stderr.getvalue(), '')

    @mock.patch.object(sys, 'stderr', StringIO.StringIO())
    @mock.patch.object(ConfigParser, 'SafeConfigParser')
    @mock.patch('logging.basicConfig')
    @mock.patch('logging.config.fileConfig')
    @mock.patch('multiprocessing.Process')
    @mock.patch('multiprocessing.Queue')
    @mock.patch('os.kill')
    @mock.patch('time.sleep')
    @mock.patch('train.request.parse_files')
    @mock.patch('train.wsgi.start_workers')
    def test_cmdline_args(self, mock_start_workers, mock_parse_files,
                          mock_sleep, mock_kill, mock_Queue, mock_Process,
                          mock_fileConfig, mock_basicConfig,
                          mock_SafeConfigParser):
        conf = self.setup_conf(turnstile=dict(a='1'))
        mock_SafeConfigParser.return_value = conf
        mock_parse_files.return_value = [
            mock.Mock(queue_request='qreq1'),
            mock.Mock(queue_request='qreq2'),
        ]
        queue = mock.Mock(**{'empty.side_effect': [False, True]})
        mock_Queue.return_value = queue
        mock_start_workers.return_value = [1234, 2345, 3456]
        procs = [
            mock.Mock(),
            mock.Mock(),
        ]
        mock_Process.side_effect = procs
        requests = ['req1', 'req2']

        runner.train('train.cfg', requests)

        mock_SafeConfigParser.assert_called_once_with()
        conf.assert_has_calls([
            mock.call.read(['train.cfg']),
            mock.call.has_section('turnstile'),
            mock.call.get('train', 'log_config'),
            mock.call.get('train', 'requests'),
            mock.call.items('turnstile'),
        ])
        self.assertEqual(len(conf.method_calls), 5)
        self.assertFalse(mock_fileConfig.called)
        mock_basicConfig.assert_called_once_with()
        mock_parse_files.assert_called_once_with(requests)
        mock_Queue.assert_called_once_with()
        mock_start_workers.assert_called_once_with(queue, [('a', '1')], 1)
        mock_Process.assert_has_calls([
            mock.call(target='qreq1', args=(queue,)),
            mock.call(target='qreq2', args=(queue,)),
        ])
        for proc in procs:
            proc.assert_has_calls([
                mock.call.start(),
                mock.call.join(),
            ])
        queue.empty.assert_has_calls([
            mock.call(),
            mock.call(),
        ])
        mock_sleep.assert_called_once_with(1)
        mock_kill.assert_has_calls([
            mock.call(1234, signal.SIGTERM),
            mock.call(2345, signal.SIGTERM),
            mock.call(3456, signal.SIGTERM),
        ])
        self.assertEqual(sys.stderr.getvalue(), '')

    @mock.patch.object(sys, 'stderr', StringIO.StringIO())
    @mock.patch.object(ConfigParser, 'SafeConfigParser')
    @mock.patch('logging.basicConfig')
    @mock.patch('logging.config.fileConfig')
    @mock.patch('multiprocessing.Process')
    @mock.patch('multiprocessing.Queue')
    @mock.patch('os.kill')
    @mock.patch('time.sleep')
    @mock.patch('train.request.parse_files')
    @mock.patch('train.wsgi.start_workers')
    def test_log_cmdline(self, mock_start_workers, mock_parse_files,
                         mock_sleep, mock_kill, mock_Queue, mock_Process,
                         mock_fileConfig, mock_basicConfig,
                         mock_SafeConfigParser):
        conf = self.setup_conf(turnstile=dict(a='1'))
        mock_SafeConfigParser.return_value = conf
        mock_parse_files.return_value = [
            mock.Mock(queue_request='qreq1'),
            mock.Mock(queue_request='qreq2'),
        ]
        queue = mock.Mock(**{'empty.return_value': True})
        mock_Queue.return_value = queue
        mock_start_workers.return_value = [1234, 2345, 3456]
        procs = [
            mock.Mock(),
            mock.Mock(),
        ]
        mock_Process.side_effect = procs
        requests = ['req1', 'req2']

        runner.train('train.cfg', requests, log_config='log.cfg')

        mock_SafeConfigParser.assert_called_once_with()
        conf.assert_has_calls([
            mock.call.read(['train.cfg']),
            mock.call.has_section('turnstile'),
            mock.call.get('train', 'requests'),
            mock.call.items('turnstile'),
        ])
        self.assertEqual(len(conf.method_calls), 4)
        mock_fileConfig.assert_called_once_with('log.cfg')
        self.assertFalse(mock_basicConfig.called)
        mock_parse_files.assert_called_once_with(requests)
        mock_Queue.assert_called_once_with()
        mock_start_workers.assert_called_once_with(queue, [('a', '1')], 1)
        mock_Process.assert_has_calls([
            mock.call(target='qreq1', args=(queue,)),
            mock.call(target='qreq2', args=(queue,)),
        ])
        for proc in procs:
            proc.assert_has_calls([
                mock.call.start(),
                mock.call.join(),
            ])
        queue.empty.assert_called_once_with()
        self.assertFalse(mock_sleep.called)
        mock_kill.assert_has_calls([
            mock.call(1234, signal.SIGTERM),
            mock.call(2345, signal.SIGTERM),
            mock.call(3456, signal.SIGTERM),
        ])
        self.assertEqual(sys.stderr.getvalue(), '')

    @mock.patch.object(sys, 'stderr', StringIO.StringIO())
    @mock.patch.object(ConfigParser, 'SafeConfigParser')
    @mock.patch('logging.basicConfig')
    @mock.patch('logging.config.fileConfig')
    @mock.patch('multiprocessing.Process')
    @mock.patch('multiprocessing.Queue')
    @mock.patch('os.kill')
    @mock.patch('time.sleep')
    @mock.patch('train.request.parse_files')
    @mock.patch('train.wsgi.start_workers')
    def test_log_conf(self, mock_start_workers, mock_parse_files,
                      mock_sleep, mock_kill, mock_Queue, mock_Process,
                      mock_fileConfig, mock_basicConfig,
                      mock_SafeConfigParser):
        conf = self.setup_conf(
            turnstile=dict(a='1'),
            train=dict(log_config='log.cfg'),
        )
        mock_SafeConfigParser.return_value = conf
        mock_parse_files.return_value = [
            mock.Mock(queue_request='qreq1'),
            mock.Mock(queue_request='qreq2'),
        ]
        queue = mock.Mock(**{'empty.return_value': True})
        mock_Queue.return_value = queue
        mock_start_workers.return_value = [1234, 2345, 3456]
        procs = [
            mock.Mock(),
            mock.Mock(),
        ]
        mock_Process.side_effect = procs
        requests = ['req1', 'req2']

        runner.train('train.cfg', requests)

        mock_SafeConfigParser.assert_called_once_with()
        conf.assert_has_calls([
            mock.call.read(['train.cfg']),
            mock.call.has_section('turnstile'),
            mock.call.get('train', 'log_config'),
            mock.call.get('train', 'requests'),
            mock.call.items('turnstile'),
        ])
        self.assertEqual(len(conf.method_calls), 5)
        mock_fileConfig.assert_called_once_with('log.cfg')
        self.assertFalse(mock_basicConfig.called)
        mock_parse_files.assert_called_once_with(requests)
        mock_Queue.assert_called_once_with()
        mock_start_workers.assert_called_once_with(queue, [('a', '1')], 1)
        mock_Process.assert_has_calls([
            mock.call(target='qreq1', args=(queue,)),
            mock.call(target='qreq2', args=(queue,)),
        ])
        for proc in procs:
            proc.assert_has_calls([
                mock.call.start(),
                mock.call.join(),
            ])
        queue.empty.assert_called_once_with()
        self.assertFalse(mock_sleep.called)
        mock_kill.assert_has_calls([
            mock.call(1234, signal.SIGTERM),
            mock.call(2345, signal.SIGTERM),
            mock.call(3456, signal.SIGTERM),
        ])
        self.assertEqual(sys.stderr.getvalue(), '')

    @mock.patch.object(sys, 'stderr', StringIO.StringIO())
    @mock.patch.object(ConfigParser, 'SafeConfigParser')
    @mock.patch('logging.basicConfig')
    @mock.patch('logging.config.fileConfig')
    @mock.patch('multiprocessing.Process')
    @mock.patch('multiprocessing.Queue')
    @mock.patch('os.kill')
    @mock.patch('time.sleep')
    @mock.patch('train.request.parse_files')
    @mock.patch('train.wsgi.start_workers')
    def test_log_badfile(self, mock_start_workers, mock_parse_files,
                         mock_sleep, mock_kill, mock_Queue, mock_Process,
                         mock_fileConfig, mock_basicConfig,
                         mock_SafeConfigParser):
        conf = self.setup_conf(turnstile=dict(a='1'))
        mock_SafeConfigParser.return_value = conf
        mock_fileConfig.side_effect = Exception("failed to read file")
        mock_parse_files.return_value = [
            mock.Mock(queue_request='qreq1'),
            mock.Mock(queue_request='qreq2'),
        ]
        queue = mock.Mock(**{'empty.return_value': True})
        mock_Queue.return_value = queue
        mock_start_workers.return_value = [1234, 2345, 3456]
        procs = [
            mock.Mock(),
            mock.Mock(),
        ]
        mock_Process.side_effect = procs
        requests = ['req1', 'req2']

        runner.train('train.cfg', requests, log_config='log.cfg')

        mock_SafeConfigParser.assert_called_once_with()
        conf.assert_has_calls([
            mock.call.read(['train.cfg']),
            mock.call.has_section('turnstile'),
            mock.call.get('train', 'requests'),
            mock.call.items('turnstile'),
        ])
        self.assertEqual(len(conf.method_calls), 4)
        mock_fileConfig.assert_called_once_with('log.cfg')
        mock_basicConfig.assert_called_once_with()
        mock_parse_files.assert_called_once_with(requests)
        mock_Queue.assert_called_once_with()
        mock_start_workers.assert_called_once_with(queue, [('a', '1')], 1)
        mock_Process.assert_has_calls([
            mock.call(target='qreq1', args=(queue,)),
            mock.call(target='qreq2', args=(queue,)),
        ])
        for proc in procs:
            proc.assert_has_calls([
                mock.call.start(),
                mock.call.join(),
            ])
        queue.empty.assert_called_once_with()
        self.assertFalse(mock_sleep.called)
        mock_kill.assert_has_calls([
            mock.call(1234, signal.SIGTERM),
            mock.call(2345, signal.SIGTERM),
            mock.call(3456, signal.SIGTERM),
        ])
        self.assertEqual(sys.stderr.getvalue(),
                         "Warning: Failed to read logging configuration "
                         "from file 'log.cfg': failed to read file\n")

    @mock.patch.object(sys, 'stderr', StringIO.StringIO())
    @mock.patch.object(ConfigParser, 'SafeConfigParser')
    @mock.patch('logging.basicConfig')
    @mock.patch('logging.config.fileConfig')
    @mock.patch('multiprocessing.Process')
    @mock.patch('multiprocessing.Queue')
    @mock.patch('os.kill')
    @mock.patch('time.sleep')
    @mock.patch('train.request.parse_files')
    @mock.patch('train.wsgi.start_workers')
    def test_alt_workers(self, mock_start_workers, mock_parse_files,
                         mock_sleep, mock_kill, mock_Queue, mock_Process,
                         mock_fileConfig, mock_basicConfig,
                         mock_SafeConfigParser):
        conf = self.setup_conf(turnstile=dict(a='1'))
        mock_SafeConfigParser.return_value = conf
        mock_parse_files.return_value = [
            mock.Mock(queue_request='qreq1'),
            mock.Mock(queue_request='qreq2'),
        ]
        queue = mock.Mock(**{'empty.return_value': True})
        mock_Queue.return_value = queue
        mock_start_workers.return_value = [1234, 2345, 3456]
        procs = [
            mock.Mock(),
            mock.Mock(),
        ]
        mock_Process.side_effect = procs
        requests = ['req1', 'req2']

        runner.train('train.cfg', requests, 23)

        mock_SafeConfigParser.assert_called_once_with()
        conf.assert_has_calls([
            mock.call.read(['train.cfg']),
            mock.call.has_section('turnstile'),
            mock.call.get('train', 'log_config'),
            mock.call.get('train', 'requests'),
            mock.call.items('turnstile'),
        ])
        self.assertEqual(len(conf.method_calls), 5)
        self.assertFalse(mock_fileConfig.called)
        mock_basicConfig.assert_called_once_with()
        mock_parse_files.assert_called_once_with(requests)
        mock_Queue.assert_called_once_with()
        mock_start_workers.assert_called_once_with(queue, [('a', '1')], 23)
        mock_Process.assert_has_calls([
            mock.call(target='qreq1', args=(queue,)),
            mock.call(target='qreq2', args=(queue,)),
        ])
        for proc in procs:
            proc.assert_has_calls([
                mock.call.start(),
                mock.call.join(),
            ])
        queue.empty.assert_called_once_with()
        self.assertFalse(mock_sleep.called)
        mock_kill.assert_has_calls([
            mock.call(1234, signal.SIGTERM),
            mock.call(2345, signal.SIGTERM),
            mock.call(3456, signal.SIGTERM),
        ])
        self.assertEqual(sys.stderr.getvalue(), '')

    @mock.patch.object(sys, 'stderr', StringIO.StringIO())
    @mock.patch.object(ConfigParser, 'SafeConfigParser')
    @mock.patch('logging.basicConfig')
    @mock.patch('logging.config.fileConfig')
    @mock.patch('multiprocessing.Process')
    @mock.patch('multiprocessing.Queue')
    @mock.patch('os.kill')
    @mock.patch('time.sleep')
    @mock.patch('train.request.parse_files')
    @mock.patch('train.wsgi.start_workers')
    def test_no_workers(self, mock_start_workers, mock_parse_files,
                        mock_sleep, mock_kill, mock_Queue, mock_Process,
                        mock_fileConfig, mock_basicConfig,
                        mock_SafeConfigParser):
        conf = self.setup_conf(turnstile=dict(a='1'))
        mock_SafeConfigParser.return_value = conf
        mock_parse_files.return_value = [
            mock.Mock(queue_request='qreq1'),
            mock.Mock(queue_request='qreq2'),
        ]
        queue = mock.Mock(**{'empty.return_value': True})
        mock_Queue.return_value = queue
        mock_start_workers.return_value = [1234, 2345, 3456]
        procs = [
            mock.Mock(),
            mock.Mock(),
        ]
        mock_Process.side_effect = procs
        requests = ['req1', 'req2']

        runner.train('train.cfg', requests, 0)

        mock_SafeConfigParser.assert_called_once_with()
        conf.assert_has_calls([
            mock.call.read(['train.cfg']),
            mock.call.has_section('turnstile'),
            mock.call.get('train', 'log_config'),
            mock.call.get('train', 'workers'),
            mock.call.get('train', 'requests'),
            mock.call.items('turnstile'),
        ])
        self.assertEqual(len(conf.method_calls), 6)
        self.assertFalse(mock_fileConfig.called)
        mock_basicConfig.assert_called_once_with()
        mock_parse_files.assert_called_once_with(requests)
        mock_Queue.assert_called_once_with()
        mock_start_workers.assert_called_once_with(queue, [('a', '1')], 1)
        mock_Process.assert_has_calls([
            mock.call(target='qreq1', args=(queue,)),
            mock.call(target='qreq2', args=(queue,)),
        ])
        for proc in procs:
            proc.assert_has_calls([
                mock.call.start(),
                mock.call.join(),
            ])
        queue.empty.assert_called_once_with()
        self.assertFalse(mock_sleep.called)
        mock_kill.assert_has_calls([
            mock.call(1234, signal.SIGTERM),
            mock.call(2345, signal.SIGTERM),
            mock.call(3456, signal.SIGTERM),
        ])
        self.assertEqual(sys.stderr.getvalue(), '')

    @mock.patch.object(sys, 'stderr', StringIO.StringIO())
    @mock.patch.object(ConfigParser, 'SafeConfigParser')
    @mock.patch('logging.basicConfig')
    @mock.patch('logging.config.fileConfig')
    @mock.patch('multiprocessing.Process')
    @mock.patch('multiprocessing.Queue')
    @mock.patch('os.kill')
    @mock.patch('time.sleep')
    @mock.patch('train.request.parse_files')
    @mock.patch('train.wsgi.start_workers')
    def test_workers_in_conf(self, mock_start_workers, mock_parse_files,
                             mock_sleep, mock_kill, mock_Queue, mock_Process,
                             mock_fileConfig, mock_basicConfig,
                             mock_SafeConfigParser):
        conf = self.setup_conf(
            turnstile=dict(a='1'),
            train=dict(workers='23'),
        )
        mock_SafeConfigParser.return_value = conf
        mock_parse_files.return_value = [
            mock.Mock(queue_request='qreq1'),
            mock.Mock(queue_request='qreq2'),
        ]
        queue = mock.Mock(**{'empty.return_value': True})
        mock_Queue.return_value = queue
        mock_start_workers.return_value = [1234, 2345, 3456]
        procs = [
            mock.Mock(),
            mock.Mock(),
        ]
        mock_Process.side_effect = procs
        requests = ['req1', 'req2']

        runner.train('train.cfg', requests, 0)

        mock_SafeConfigParser.assert_called_once_with()
        conf.assert_has_calls([
            mock.call.read(['train.cfg']),
            mock.call.has_section('turnstile'),
            mock.call.get('train', 'log_config'),
            mock.call.get('train', 'workers'),
            mock.call.get('train', 'requests'),
            mock.call.items('turnstile'),
        ])
        self.assertEqual(len(conf.method_calls), 6)
        self.assertFalse(mock_fileConfig.called)
        mock_basicConfig.assert_called_once_with()
        mock_parse_files.assert_called_once_with(requests)
        mock_Queue.assert_called_once_with()
        mock_start_workers.assert_called_once_with(queue, [('a', '1')], 23)
        mock_Process.assert_has_calls([
            mock.call(target='qreq1', args=(queue,)),
            mock.call(target='qreq2', args=(queue,)),
        ])
        for proc in procs:
            proc.assert_has_calls([
                mock.call.start(),
                mock.call.join(),
            ])
        queue.empty.assert_called_once_with()
        self.assertFalse(mock_sleep.called)
        mock_kill.assert_has_calls([
            mock.call(1234, signal.SIGTERM),
            mock.call(2345, signal.SIGTERM),
            mock.call(3456, signal.SIGTERM),
        ])
        self.assertEqual(sys.stderr.getvalue(), '')

    @mock.patch.object(sys, 'stderr', StringIO.StringIO())
    @mock.patch.object(ConfigParser, 'SafeConfigParser')
    @mock.patch('logging.basicConfig')
    @mock.patch('logging.config.fileConfig')
    @mock.patch('multiprocessing.Process')
    @mock.patch('multiprocessing.Queue')
    @mock.patch('os.kill')
    @mock.patch('time.sleep')
    @mock.patch('train.request.parse_files')
    @mock.patch('train.wsgi.start_workers')
    def test_workers_in_conf_bad(self, mock_start_workers, mock_parse_files,
                                 mock_sleep, mock_kill, mock_Queue,
                                 mock_Process, mock_fileConfig,
                                 mock_basicConfig, mock_SafeConfigParser):
        conf = self.setup_conf(
            turnstile=dict(a='1'),
            train=dict(workers='23a'),
        )
        mock_SafeConfigParser.return_value = conf
        mock_parse_files.return_value = [
            mock.Mock(queue_request='qreq1'),
            mock.Mock(queue_request='qreq2'),
        ]
        queue = mock.Mock(**{'empty.return_value': True})
        mock_Queue.return_value = queue
        mock_start_workers.return_value = [1234, 2345, 3456]
        procs = [
            mock.Mock(),
            mock.Mock(),
        ]
        mock_Process.side_effect = procs
        requests = ['req1', 'req2']

        runner.train('train.cfg', requests, 0)

        mock_SafeConfigParser.assert_called_once_with()
        conf.assert_has_calls([
            mock.call.read(['train.cfg']),
            mock.call.has_section('turnstile'),
            mock.call.get('train', 'log_config'),
            mock.call.get('train', 'workers'),
            mock.call.get('train', 'requests'),
            mock.call.items('turnstile'),
        ])
        self.assertEqual(len(conf.method_calls), 6)
        self.assertFalse(mock_fileConfig.called)
        mock_basicConfig.assert_called_once_with()
        mock_parse_files.assert_called_once_with(requests)
        mock_Queue.assert_called_once_with()
        mock_start_workers.assert_called_once_with(queue, [('a', '1')], 1)
        mock_Process.assert_has_calls([
            mock.call(target='qreq1', args=(queue,)),
            mock.call(target='qreq2', args=(queue,)),
        ])
        for proc in procs:
            proc.assert_has_calls([
                mock.call.start(),
                mock.call.join(),
            ])
        queue.empty.assert_called_once_with()
        self.assertFalse(mock_sleep.called)
        mock_kill.assert_has_calls([
            mock.call(1234, signal.SIGTERM),
            mock.call(2345, signal.SIGTERM),
            mock.call(3456, signal.SIGTERM),
        ])
        self.assertEqual(sys.stderr.getvalue(), '')

    @mock.patch.object(sys, 'stderr', StringIO.StringIO())
    @mock.patch.object(ConfigParser, 'SafeConfigParser')
    @mock.patch('logging.basicConfig')
    @mock.patch('logging.config.fileConfig')
    @mock.patch('multiprocessing.Process')
    @mock.patch('multiprocessing.Queue')
    @mock.patch('os.kill')
    @mock.patch('time.sleep')
    @mock.patch('train.request.parse_files')
    @mock.patch('train.wsgi.start_workers')
    def test_requests_in_conf(self, mock_start_workers, mock_parse_files,
                              mock_sleep, mock_kill, mock_Queue, mock_Process,
                              mock_fileConfig, mock_basicConfig,
                              mock_SafeConfigParser):
        conf = self.setup_conf(
            turnstile=dict(a='1'),
            train=dict(requests='  req3  req4    req5 '),
        )
        mock_SafeConfigParser.return_value = conf
        mock_parse_files.return_value = [
            mock.Mock(queue_request='qreq1'),
            mock.Mock(queue_request='qreq2'),
        ]
        queue = mock.Mock(**{'empty.return_value': True})
        mock_Queue.return_value = queue
        mock_start_workers.return_value = [1234, 2345, 3456]
        procs = [
            mock.Mock(),
            mock.Mock(),
        ]
        mock_Process.side_effect = procs
        requests = ['req1', 'req2']

        runner.train('train.cfg', requests)

        mock_SafeConfigParser.assert_called_once_with()
        conf.assert_has_calls([
            mock.call.read(['train.cfg']),
            mock.call.has_section('turnstile'),
            mock.call.get('train', 'log_config'),
            mock.call.get('train', 'requests'),
            mock.call.items('turnstile'),
        ])
        self.assertEqual(len(conf.method_calls), 5)
        self.assertFalse(mock_fileConfig.called)
        mock_basicConfig.assert_called_once_with()
        mock_parse_files.assert_called_once_with(
            ['req1', 'req2', 'req3', 'req4', 'req5'])
        mock_Queue.assert_called_once_with()
        mock_start_workers.assert_called_once_with(queue, [('a', '1')], 1)
        mock_Process.assert_has_calls([
            mock.call(target='qreq1', args=(queue,)),
            mock.call(target='qreq2', args=(queue,)),
        ])
        for proc in procs:
            proc.assert_has_calls([
                mock.call.start(),
                mock.call.join(),
            ])
        queue.empty.assert_called_once_with()
        self.assertFalse(mock_sleep.called)
        mock_kill.assert_has_calls([
            mock.call(1234, signal.SIGTERM),
            mock.call(2345, signal.SIGTERM),
            mock.call(3456, signal.SIGTERM),
        ])
        self.assertEqual(sys.stderr.getvalue(), '')
