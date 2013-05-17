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

import signal

import mock
import unittest2

from train import util


class TestStackedDict(unittest2.TestCase):
    def test_init(self):
        sd = util.StackedDict('parent')

        self.assertEqual(sd._parent, 'parent')
        self.assertEqual(sd._deleted, set())
        self.assertEqual(sd._values, {})

    def test_getitem_deleted(self):
        sd = util.StackedDict(dict(spam='spammer'))
        sd._values['spam'] = 'alternate'
        sd._deleted.add('spam')

        with self.assertRaises(KeyError):
            dummy = sd['spam']

    def test_getitem_local(self):
        sd = util.StackedDict(dict(spam='spammer'))
        sd._values['spam'] = 'alternate'

        self.assertEqual(sd['spam'], 'alternate')

    def test_getitem_noparent(self):
        sd = util.StackedDict()

        with self.assertRaises(KeyError):
            dummy = sd['spam']

    def test_getitem_parent(self):
        sd = util.StackedDict(dict(spam='spammer'))

        self.assertEqual(sd['spam'], 'spammer')

    def test_setitem(self):
        sd = util.StackedDict()
        sd._deleted = set(['foobar'])

        sd['spam'] = 'alternate'

        self.assertEqual(sd._values, dict(spam='alternate'))
        self.assertEqual(sd._deleted, set(['foobar']))

    def test_setitem_deleted(self):
        sd = util.StackedDict()
        sd._deleted = set(['foobar', 'spam'])

        sd['spam'] = 'alternate'

        self.assertEqual(sd._values, dict(spam='alternate'))
        self.assertEqual(sd._deleted, set(['foobar']))

    def test_delitem_deleted(self):
        sd = util.StackedDict(dict(spam='spammer'))
        sd._deleted = set(['spam'])

        with self.assertRaises(KeyError):
            del sd['spam']

        self.assertEqual(sd._deleted, set(['spam']))
        self.assertEqual(sd._values, {})

    def test_delitem_local(self):
        sd = util.StackedDict(dict(spam='spammer'))
        sd._values['spam'] = 'alternate'

        del sd['spam']

        self.assertEqual(sd._deleted, set(['spam']))
        self.assertEqual(sd._values, {})

    def test_delitem_noparent(self):
        sd = util.StackedDict()

        with self.assertRaises(KeyError):
            del sd['spam']

        self.assertEqual(sd._deleted, set())
        self.assertEqual(sd._values, {})

    def test_delitem_parent_nokey(self):
        sd = util.StackedDict({})

        with self.assertRaises(KeyError):
            del sd['spam']

        self.assertEqual(sd._deleted, set())
        self.assertEqual(sd._values, {})

    def test_delitem_parent_only(self):
        sd = util.StackedDict(dict(spam='spammer'))

        del sd['spam']

        self.assertEqual(sd._deleted, set(['spam']))
        self.assertEqual(sd._values, {})

    def test_iter_noparent(self):
        sd = util.StackedDict()
        sd._values = dict(a=1, b=2, c=3)

        result = list(iter(sd))

        self.assertEqual(len(result), 3)
        self.assertEqual(set(result), set('abc'))

    def test_iter_withparent(self):
        sd = util.StackedDict(dict(b=2, d=4, e=5, f=6, g=7))
        sd._deleted = set('fg')
        sd._values = dict(a=1, b=2, c=3)

        result = list(iter(sd))

        self.assertEqual(len(result), 5)
        self.assertEqual(set(result), set('abcde'))

    def test_len(self):
        sd = util.StackedDict(dict(b=2, d=4, e=5, f=6, g=7))
        sd._deleted = set('fg')
        sd._values = dict(a=1, b=2, c=3)

        result = len(sd)

        self.assertEqual(result, 5)

    def test_reset_deleted(self):
        sd = util.StackedDict()
        sd._deleted = set(['foobar', 'spam'])
        sd._values = dict(barfoo='foobar')

        sd.reset('spam')

        self.assertEqual(sd._deleted, set(['foobar']))
        self.assertEqual(sd._values, dict(barfoo='foobar'))

    def test_reset_overridden(self):
        sd = util.StackedDict()
        sd._deleted = set(['foobar'])
        sd._values = dict(barfoo='foobar', spam='spammer')

        sd.reset('spam')

        self.assertEqual(sd._deleted, set(['foobar']))
        self.assertEqual(sd._values, dict(barfoo='foobar'))

    def test_reset_all(self):
        sd = util.StackedDict()
        sd._deleted = set(['foobar'])
        sd._values = dict(barfoo='foobar')

        sd.reset()

        self.assertEqual(sd._deleted, set())
        self.assertEqual(sd._values, {})

    def test_copy(self):
        parent = dict(b=22, d=4, e=5, f=6, g=7)
        sd = util.StackedDict(parent)
        sd._deleted = set('fg')
        sd._values = dict(a=1, b=2, c=3)

        result = sd.copy()

        del parent['d']
        parent['e'] = 55
        sd._deleted.add('a')
        del sd._values['a']
        del sd._values['b']
        sd._values['f'] = 66

        self.assertEqual(result, dict(a=1, b=2, c=3, d=4, e=5))


class TestSignalExit(unittest2.TestCase):
    def test_init(self):
        se = util.SignalExit(signal.SIGTERM, 25)

        self.assertEqual(se.signo, signal.SIGTERM)
        self.assertEqual(se.code, 25)


class TestException(BaseException):
    pass


class TestLauncher(unittest2.TestCase):
    def test_class_attrs(self):
        self.assertEqual(util.Launcher.signames[signal.SIGTERM], 'SIGTERM')
        self.assertEqual(util.Launcher.signames[signal.SIGINT], 'SIGINT')
        self.assertTrue(signal.SIGTERM in util.Launcher.death_sigs)
        self.assertTrue(signal.SIGINT in util.Launcher.death_sigs)

    def test_init_noargs(self):
        self.assertRaises(TypeError, util.Launcher, a=1, b=2, c=3)

    def test_init(self):
        launcher = util.Launcher('start', 'arg1', 'arg2', 'arg3',
                                 a='arg4', b='arg5', c='arg6')

        self.assertEqual(launcher.start_func, 'start')
        self.assertEqual(launcher.start_args, ('arg1', 'arg2', 'arg3'))
        self.assertEqual(launcher.start_kwargs,
                         dict(a='arg4', b='arg5', c='arg6'))

    @mock.patch.object(signal, 'signal')
    def test_install_handler(self, mock_signal):
        launcher = util.Launcher('start')

        launcher._install_handler('handler')

        mock_signal.assert_has_calls([
            mock.call(signal.SIGTERM, 'handler'),
            mock.call(signal.SIGINT, 'handler'),
        ], any_order=True)

    @mock.patch.object(util.Launcher, '_install_handler')
    def test_handle_signal(self, mock_install_handler):
        launcher = util.Launcher('start')

        with self.assertRaises(util.SignalExit) as exc:
            launcher._handle_signal(25, 'some frame')

        self.assertEqual(exc.exception.signo, 25)
        mock_install_handler.assert_called_once_with(signal.SIG_DFL)

    @mock.patch('os.getpid', return_value=5678)
    @mock.patch('os.fork', return_value=1234)
    @mock.patch('os._exit')
    @mock.patch.object(util, 'LOG')
    @mock.patch.object(util.Launcher, '_install_handler')
    def test_start_parent(self, mock_install_handler, mock_LOG, mock_exit,
                          mock_fork, mock_getpid):
        starter = mock.Mock()
        launcher = util.Launcher(starter)

        result = launcher.start()

        self.assertEqual(result, 1234)
        mock_fork.assert_called_once_with()
        self.assertFalse(mock_install_handler.called)
        self.assertFalse(mock_getpid.called)
        self.assertFalse(starter.called)
        self.assertEqual(mock_LOG.method_calls, [])
        self.assertFalse(mock_exit.called)

    @mock.patch('os.getpid', return_value=1234)
    @mock.patch('os.fork', return_value=0)
    @mock.patch('os._exit')
    @mock.patch.object(util, 'LOG')
    @mock.patch.object(util.Launcher, '_install_handler')
    def test_start_normal(self, mock_install_handler, mock_LOG, mock_exit,
                          mock_fork, mock_getpid):
        starter = mock.Mock()
        launcher = util.Launcher(starter, 'arg1', 'arg2', a='arg3', b='arg4')

        result = launcher.start()

        self.assertEqual(result, None)
        mock_fork.assert_called_once_with()
        mock_install_handler.assert_called_once_with(launcher._handle_signal)
        mock_getpid.assert_called_once_with()
        starter.assert_called_once_with('arg1', 'arg2', a='arg3', b='arg4')
        self.assertEqual(mock_LOG.method_calls, [])
        mock_exit.assert_called_once_with(0)

    @mock.patch('os.getpid', return_value=1234)
    @mock.patch('os.fork', return_value=0)
    @mock.patch('os._exit')
    @mock.patch.object(util, 'LOG')
    @mock.patch.object(util.Launcher, '_install_handler')
    def test_start_signal(self, mock_install_handler, mock_LOG, mock_exit,
                          mock_fork, mock_getpid):
        starter = mock.Mock(side_effect=util.SignalExit(signal.SIGTERM))
        launcher = util.Launcher(starter)

        result = launcher.start()

        self.assertEqual(result, None)
        mock_fork.assert_called_once_with()
        mock_install_handler.assert_called_once_with(launcher._handle_signal)
        mock_getpid.assert_called_once_with()
        starter.assert_called_once_with()
        mock_LOG.assert_has_calls([
            mock.call.info("1234: Caught SIGTERM, exiting"),
        ])
        self.assertEqual(len(mock_LOG.method_calls), 1)
        mock_exit.assert_called_once_with(1)

    @mock.patch('os.getpid', return_value=1234)
    @mock.patch('os.fork', return_value=0)
    @mock.patch('os._exit')
    @mock.patch.object(util, 'LOG')
    @mock.patch.object(util.Launcher, '_install_handler')
    def test_start_exit(self, mock_install_handler, mock_LOG, mock_exit,
                        mock_fork, mock_getpid):
        starter = mock.Mock(side_effect=SystemExit(5))
        launcher = util.Launcher(starter)

        result = launcher.start()

        self.assertEqual(result, None)
        mock_fork.assert_called_once_with()
        mock_install_handler.assert_called_once_with(launcher._handle_signal)
        mock_getpid.assert_called_once_with()
        starter.assert_called_once_with()
        self.assertEqual(mock_LOG.method_calls, [])
        mock_exit.assert_called_once_with(5)

    @mock.patch('os.getpid', return_value=1234)
    @mock.patch('os.fork', return_value=0)
    @mock.patch('os._exit')
    @mock.patch.object(util, 'LOG')
    @mock.patch.object(util.Launcher, '_install_handler')
    def test_start_exception(self, mock_install_handler, mock_LOG, mock_exit,
                             mock_fork, mock_getpid):
        starter = mock.Mock(side_effect=TestException)
        launcher = util.Launcher(starter)

        result = launcher.start()

        self.assertEqual(result, None)
        mock_fork.assert_called_once_with()
        mock_install_handler.assert_called_once_with(launcher._handle_signal)
        mock_getpid.assert_called_once_with()
        starter.assert_called_once_with()
        mock_LOG.assert_has_calls([
            mock.call.exception("1234: Unhandled exception"),
        ])
        self.assertEqual(len(mock_LOG.method_calls), 1)
        mock_exit.assert_called_once_with(2)
