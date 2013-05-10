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

from train import request


class TestSequence(unittest2.TestCase):
    def test_init(self):
        headers = dict(a=1, b=2, c=3)
        seq = request.Sequence('test_seq', headers)

        self.assertEqual(seq.name, 'test_seq')
        self.assertEqual(seq.headers, dict(a=1, b=2, c=3))
        self.assertEqual(seq.requests, [])

        # Verify header independence
        headers['d'] = 4
        self.assertEqual(seq.headers, dict(a=1, b=2, c=3))

    def test_getitem(self):
        headers = dict(a=1, b=2, c=3)
        seq = request.Sequence('test_seq', headers)

        self.assertEqual(seq['a'], 1)
        with self.assertRaises(KeyError):
            dummy = seq['d']

    def test_setitem(self):
        headers = dict(a=1, b=2, c=3)
        seq = request.Sequence('test_seq', headers)

        seq['a'] = 5
        seq['d'] = 6

        self.assertEqual(seq.headers, dict(a=5, b=2, c=3, d=6))

    def test_delitem(self):
        headers = dict(a=1, b=2, c=3)
        seq = request.Sequence('test_seq', headers)

        del seq['a']
        self.assertEqual(seq.headers, dict(b=2, c=3))

        with self.assertRaises(KeyError):
            del seq['d']

    def test_push(self):
        seq = request.Sequence('test_seq', {})

        seq.push('request1')
        seq.push('gap')
        seq.push('request2')

        self.assertEqual(seq.requests, ['request1', 'gap', 'request2'])


class TestRequest(unittest2.TestCase):
    def test_init(self):
        headers = dict(a=1, b=2, c=3)
        req = request.Request(mock.Mock(headers=headers), 'get', 'uri')

        self.assertEqual(req.method, 'GET')
        self.assertEqual(req.uri, 'uri')
        self.assertEqual(req.headers, dict(a=1, b=2, c=3))

        # Verify header independence
        headers['d'] = 4
        self.assertEqual(req.headers, dict(a=1, b=2, c=3))

    def test_getitem(self):
        headers = dict(a=1, b=2, c=3)
        req = request.Request(mock.Mock(headers=headers), 'get', 'uri')

        self.assertEqual(req['a'], 1)
        with self.assertRaises(KeyError):
            dummy = req['d']

    def test_setitem(self):
        headers = dict(a=1, b=2, c=3)
        req = request.Request(mock.Mock(headers=headers), 'get', 'uri')

        req['a'] = 5
        req['d'] = 6

        self.assertEqual(req.headers, dict(a=5, b=2, c=3, d=6))

    def test_delitem(self):
        headers = dict(a=1, b=2, c=3)
        req = request.Request(mock.Mock(headers=headers), 'get', 'uri')

        del req['a']
        self.assertEqual(req.headers, dict(b=2, c=3))

        with self.assertRaises(KeyError):
            del req['d']


class TestGap(unittest2.TestCase):
    def test_init(self):
        gap = request.Gap(18.23)

        self.assertEqual(gap.delta, 18.23)


class TestPartialHeader(unittest2.TestCase):
    def test_init(self):
        header = request.PartialHeader('x-random_header',
                                       "this   is\t\ta\n\rtest")

        self.assertEqual(header.name, 'X_RANDOM_HEADER')
        self.assertEqual(header.value, "this is a test")

    def test_iadd(self):
        header = request.PartialHeader('x-random-header', "this")

        header += "is   a\t\r\n  test"

        self.assertEqual(header.value, "this is a test")

    def test_apply(self):
        obj = {}
        header = request.PartialHeader('x-random-header', "this is a test")

        header.apply(obj)

        self.assertEqual(obj, {'X_RANDOM_HEADER': "this is a test"})


class TestRequestParseState(unittest2.TestCase):
    def test_init(self):
        state = request.RequestParseState()

        self.assertEqual(state._headers, {})
        self.assertEqual(state._sequences, {})
        self.assertEqual(state._sequence, None)
        self.assertEqual(state._request, None)
        self.assertEqual(state._header, None)

    @mock.patch.object(request.RequestParseState, 'finish_header')
    @mock.patch.object(request, 'Sequence', return_value='new_seq')
    def test_start_sequence_to_global(self, mock_Sequence, mock_finish_header):
        state = request.RequestParseState()
        state._request = 'request'
        state._sequence = 'sequence'
        state._sequences['spam'] = 'spam_seq'

        state.start_sequence('filename', '')

        self.assertFalse(mock_finish_header.called)
        self.assertFalse(mock_Sequence.called)
        self.assertEqual(state._request, None)
        self.assertEqual(state._sequence, None)
        self.assertEqual(state._sequences, dict(spam='spam_seq'))

    @mock.patch.object(request.RequestParseState, 'finish_header')
    @mock.patch.object(request, 'Sequence', return_value='new_seq')
    def test_start_sequence_finish_header(self, mock_Sequence,
                                          mock_finish_header):
        state = request.RequestParseState()
        state._header = 'header'
        state._request = 'request'
        state._sequence = 'sequence'
        state._sequences['spam'] = 'spam_seq'

        state.start_sequence('filename', '')

        mock_finish_header.assert_called_once_with('filename')
        self.assertFalse(mock_Sequence.called)
        self.assertEqual(state._request, None)
        self.assertEqual(state._sequence, None)
        self.assertEqual(state._sequences, dict(spam='spam_seq'))

    @mock.patch.object(request.RequestParseState, 'finish_header')
    @mock.patch.object(request, 'Sequence', return_value='new_seq')
    def test_start_sequence_existing(self, mock_Sequence, mock_finish_header):
        state = request.RequestParseState()
        state._request = 'request'
        state._sequences['spam'] = 'spam_seq'

        state.start_sequence('filename', 'spam')

        self.assertFalse(mock_finish_header.called)
        self.assertFalse(mock_Sequence.called)
        self.assertEqual(state._request, None)
        self.assertEqual(state._sequence, 'spam_seq')
        self.assertEqual(state._sequences, dict(spam='spam_seq'))

    @mock.patch.object(request.RequestParseState, 'finish_header')
    @mock.patch.object(request, 'Sequence', return_value='new_seq')
    def test_start_sequence_new(self, mock_Sequence, mock_finish_header):
        state = request.RequestParseState()
        state._headers = dict(HEADER1='value1', HEADER2='value2')
        state._request = 'request'
        state._sequences['spam'] = 'spam_seq'

        state.start_sequence('filename', 'other')

        self.assertFalse(mock_finish_header.called)
        mock_Sequence.assert_called_once_with(
            'other', dict(HEADER1='value1', HEADER2='value2'))
        self.assertEqual(state._request, None)
        self.assertEqual(state._sequence, 'new_seq')
        self.assertEqual(state._sequences, dict(
            spam='spam_seq',
            other='new_seq',
        ))

    @mock.patch.object(request.RequestParseState, 'finish_header')
    @mock.patch.object(request, 'Request', return_value='new_req')
    def test_start_request_bad_state(self, mock_Request, mock_finish_header):
        state = request.RequestParseState()
        state._header = 'header'
        state._request = 'request'

        self.assertRaises(request.RequestParseException, state.start_request,
                          'filename', 'get', 'uri')

        self.assertEqual(state._request, 'request')
        self.assertFalse(mock_finish_header.called)
        self.assertFalse(mock_Request.called)

    @mock.patch.object(request.RequestParseState, 'finish_header')
    @mock.patch.object(request, 'Request', return_value='new_req')
    def test_start_request(self, mock_Request, mock_finish_header):
        state = request.RequestParseState()
        state._sequence = mock.Mock()
        state._request = 'request'

        state.start_request('filename', 'get', 'uri')

        self.assertEqual(state._request, 'new_req')
        self.assertFalse(mock_finish_header.called)
        mock_Request.assert_called_once_with(state._sequence, 'get', 'uri')
        state._sequence.push.assert_called_once_with('new_req')

    @mock.patch.object(request.RequestParseState, 'finish_header')
    @mock.patch.object(request, 'Request', return_value='new_req')
    def test_start_request_finish_header(self, mock_Request,
                                         mock_finish_header):
        state = request.RequestParseState()
        state._sequence = mock.Mock()
        state._header = 'header'
        state._request = 'request'

        state.start_request('filename', 'get', 'uri')

        self.assertEqual(state._request, 'new_req')
        mock_finish_header.assert_called_once_with('filename')
        mock_Request.assert_called_once_with(state._sequence, 'get', 'uri')
        state._sequence.push.assert_called_once_with('new_req')

    @mock.patch.object(request.RequestParseState, 'finish_header')
    @mock.patch.object(request, 'Gap', return_value='gap')
    def test_push_gap_bad_state(self, mock_Gap, mock_finish_header):
        state = request.RequestParseState()
        state._header = 'header'
        state._request = 'request'

        self.assertRaises(request.RequestParseException, state.push_gap,
                          'filename', 12.34)

        self.assertEqual(state._request, 'request')
        self.assertFalse(mock_finish_header.called)
        self.assertFalse(mock_Gap.called)

    @mock.patch.object(request.RequestParseState, 'finish_header')
    @mock.patch.object(request, 'Gap', return_value='gap')
    def test_push_gap(self, mock_Gap, mock_finish_header):
        state = request.RequestParseState()
        state._sequence = mock.Mock()
        state._request = 'request'

        state.push_gap('filename', 12.34)

        self.assertEqual(state._request, None)
        self.assertFalse(mock_finish_header.called)
        mock_Gap.assert_called_once_with(12.34)
        state._sequence.push.assert_called_once_with('gap')

    @mock.patch.object(request.RequestParseState, 'finish_header')
    @mock.patch.object(request, 'Gap', return_value='gap')
    def test_push_gap_finish_header(self, mock_Gap, mock_finish_header):
        state = request.RequestParseState()
        state._sequence = mock.Mock()
        state._header = 'header'
        state._request = 'request'

        state.push_gap('filename', 12.34)

        self.assertEqual(state._request, None)
        mock_finish_header.assert_called_once_with('filename')
        mock_Gap.assert_called_once_with(12.34)
        state._sequence.push.assert_called_once_with('gap')

    @mock.patch.object(request.RequestParseState, 'finish_header')
    @mock.patch.object(request, 'PartialHeader', return_value='header')
    def test_start_header(self, mock_PartialHeader, mock_finish_header):
        state = request.RequestParseState()

        state.start_header('filename', 'header', 'value')

        self.assertEqual(state._header, 'header')
        self.assertFalse(mock_finish_header.called)
        mock_PartialHeader.assert_called_once_with('header', 'value')

    @mock.patch.object(request.RequestParseState, 'finish_header')
    @mock.patch.object(request, 'PartialHeader', return_value='header')
    def test_start_header_finish_header(self, mock_PartialHeader,
                                        mock_finish_header):
        state = request.RequestParseState()
        state._header = 'old_header'

        state.start_header('filename', 'header', 'value')

        self.assertEqual(state._header, 'header')
        mock_finish_header.assert_called_once_with('filename')
        mock_PartialHeader.assert_called_once_with('header', 'value')

    def test_extend_header_bad_state(self):
        state = request.RequestParseState()

        self.assertRaises(request.RequestParseException, state.extend_header,
                          'filename', 'a test')
        self.assertEqual(state._header, None)

    def test_extend_header(self):
        state = request.RequestParseState()
        state._header = "this is "

        state.extend_header('filename', 'a test')

        self.assertEqual(state._header, 'this is a test')

    def test_finish_header_request(self):
        header = mock.Mock()
        state = request.RequestParseState()
        state._header = header
        state._request = 'request'
        state._sequence = 'sequence'
        state._headers = 'headers'

        state.finish_header('filename')

        self.assertEqual(state._header, None)
        header.apply.assert_called_once_with('request')

    def test_finish_header_sequence(self):
        header = mock.Mock()
        state = request.RequestParseState()
        state._header = header
        state._sequence = 'sequence'
        state._headers = 'headers'

        state.finish_header('filename')

        self.assertEqual(state._header, None)
        header.apply.assert_called_once_with('sequence')

    def test_finish_header_global(self):
        header = mock.Mock()
        state = request.RequestParseState()
        state._header = header
        state._headers = 'headers'

        state.finish_header('filename')

        self.assertEqual(state._header, None)
        header.apply.assert_called_once_with('headers')

    @mock.patch.object(request.RequestParseState, 'finish_header')
    def test_finish(self, mock_finish_header):
        state = request.RequestParseState()
        state._sequence = 'sequence'
        state._request = 'request'

        state.finish('filename')

        self.assertFalse(mock_finish_header.called)
        self.assertEqual(state._sequence, None)
        self.assertEqual(state._request, None)
        self.assertEqual(state._header, None)

    @mock.patch.object(request.RequestParseState, 'finish_header')
    def test_finish_finish_header(self, mock_finish_header):
        state = request.RequestParseState()
        state._sequence = 'sequence'
        state._request = 'request'
        state._header = 'header'

        state.finish('filename')

        mock_finish_header.assert_called_once_with('filename')
        self.assertEqual(state._sequence, None)
        self.assertEqual(state._request, None)
        self.assertEqual(state._header, None)

    def test_sequences(self):
        state = request.RequestParseState()
        state._sequences = dict(a=1, b=2, c=3)

        self.assertEqual(set(state.sequences), set([1, 2, 3]))
