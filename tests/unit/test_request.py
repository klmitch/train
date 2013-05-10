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
from train import util


class TestSequence(unittest2.TestCase):
    def test_init(self):
        headers = dict(a=1, b=2, c=3)
        seq = request.Sequence('test_seq', headers)

        self.assertEqual(seq.name, 'test_seq')
        self.assertIsInstance(seq.headers, util.StackedDict)
        self.assertEqual(seq.headers, dict(a=1, b=2, c=3))
        self.assertEqual(seq.requests, [])

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
        self.assertIsInstance(req.headers, util.StackedDict)
        self.assertEqual(req.headers, dict(a=1, b=2, c=3))

    def test_fix(self):
        headers = dict(a=1, b=2, c=3)
        req = request.Request(mock.Mock(headers=headers), 'get', 'uri')
        req.headers['d'] = 4

        req.fix()

        headers['e'] = 5

        self.assertIsInstance(req.headers, dict)
        self.assertEqual(req.headers, dict(a=1, b=2, c=3, d=4))


class TestGap(unittest2.TestCase):
    def test_init(self):
        gap = request.Gap(18.23)

        self.assertEqual(gap.delta, 18.23)


class TestPartialHeader(unittest2.TestCase):
    def test_canon_name(self):
        result = request.PartialHeader.canon_name('x-random_header')

        self.assertEqual(result, 'X_RANDOM_HEADER')

    def test_init(self):
        header = request.PartialHeader('x-random_header',
                                       "this   is\t\ta\n\rtest")

        self.assertEqual(header.name, 'X_RANDOM_HEADER')
        self.assertEqual(header.value, "this is a test")

    def test_iadd(self):
        header = request.PartialHeader('x-random-header', "this")

        header += "is   a\t\r\n  test"

        self.assertEqual(header.value, "this is a test")


class TestRequestParseState(unittest2.TestCase):
    def test_init(self):
        state = request.RequestParseState()

        self.assertIsInstance(state._headers, util.StackedDict)
        self.assertEqual(state._headers, {})
        self.assertEqual(state._sequences, {})
        self.assertEqual(state._sequence, None)
        self.assertEqual(state._request, None)
        self.assertEqual(state._header, None)

    @mock.patch.object(request.RequestParseState, 'finish_request')
    @mock.patch.object(request.RequestParseState, 'finish_header')
    @mock.patch.object(request, 'Sequence', return_value='new_seq')
    def test_start_sequence_to_global(self, mock_Sequence, mock_finish_header,
                                      mock_finish_request):
        state = request.RequestParseState()
        state._sequence = 'sequence'
        state._sequences['spam'] = 'spam_seq'

        state.start_sequence('filename', '')

        self.assertFalse(mock_finish_request.called)
        self.assertFalse(mock_finish_header.called)
        self.assertFalse(mock_Sequence.called)
        self.assertEqual(state._sequence, None)
        self.assertEqual(state._sequences, dict(spam='spam_seq'))

    @mock.patch.object(request.RequestParseState, 'finish_request')
    @mock.patch.object(request.RequestParseState, 'finish_header')
    @mock.patch.object(request, 'Sequence', return_value='new_seq')
    def test_start_sequence_finishes(self, mock_Sequence,
                                     mock_finish_header,
                                     mock_finish_request):
        state = request.RequestParseState()
        state._header = 'header'
        state._request = 'request'
        state._sequence = 'sequence'
        state._sequences['spam'] = 'spam_seq'

        state.start_sequence('filename', '')

        mock_finish_request.assert_called_once_with('filename')
        mock_finish_header.assert_called_once_with('filename')
        self.assertFalse(mock_Sequence.called)
        self.assertEqual(state._sequence, None)
        self.assertEqual(state._sequences, dict(spam='spam_seq'))

    @mock.patch.object(request.RequestParseState, 'finish_request')
    @mock.patch.object(request.RequestParseState, 'finish_header')
    @mock.patch.object(request, 'Sequence', return_value='new_seq')
    def test_start_sequence_existing(self, mock_Sequence, mock_finish_header,
                                     mock_finish_request):
        state = request.RequestParseState()
        state._sequences['spam'] = 'spam_seq'

        state.start_sequence('filename', 'spam')

        self.assertFalse(mock_finish_request.called)
        self.assertFalse(mock_finish_header.called)
        self.assertFalse(mock_Sequence.called)
        self.assertEqual(state._sequence, 'spam_seq')
        self.assertEqual(state._sequences, dict(spam='spam_seq'))

    @mock.patch.object(request.RequestParseState, 'finish_request')
    @mock.patch.object(request.RequestParseState, 'finish_header')
    @mock.patch.object(request, 'Sequence', return_value='new_seq')
    def test_start_sequence_new(self, mock_Sequence, mock_finish_header,
                                mock_finish_request):
        state = request.RequestParseState()
        state._headers = dict(HEADER1='value1', HEADER2='value2')
        state._sequences['spam'] = 'spam_seq'

        state.start_sequence('filename', 'other')

        self.assertFalse(mock_finish_request.called)
        self.assertFalse(mock_finish_header.called)
        mock_Sequence.assert_called_once_with(
            'other', dict(HEADER1='value1', HEADER2='value2'))
        self.assertEqual(state._sequence, 'new_seq')
        self.assertEqual(state._sequences, dict(
            spam='spam_seq',
            other='new_seq',
        ))

    @mock.patch.object(request.RequestParseState, 'finish_request')
    @mock.patch.object(request.RequestParseState, 'finish_header')
    @mock.patch.object(request, 'Request', return_value='new_req')
    def test_start_request_bad_state(self, mock_Request, mock_finish_header,
                                     mock_finish_request):
        state = request.RequestParseState()
        state._header = 'header'
        state._request = 'request'

        self.assertRaises(request.RequestParseException, state.start_request,
                          'filename', 'get', 'uri')

        self.assertEqual(state._request, 'request')
        self.assertFalse(mock_finish_request.called)
        self.assertFalse(mock_finish_header.called)
        self.assertFalse(mock_Request.called)

    @mock.patch.object(request.RequestParseState, 'finish_request')
    @mock.patch.object(request.RequestParseState, 'finish_header')
    @mock.patch.object(request, 'Request', return_value='new_req')
    def test_start_request(self, mock_Request, mock_finish_header,
                           mock_finish_request):
        state = request.RequestParseState()
        state._sequence = mock.Mock()

        state.start_request('filename', 'get', 'uri')

        self.assertEqual(state._request, 'new_req')
        self.assertFalse(mock_finish_request.called)
        self.assertFalse(mock_finish_header.called)
        mock_Request.assert_called_once_with(state._sequence, 'get', 'uri')
        state._sequence.push.assert_called_once_with('new_req')

    @mock.patch.object(request.RequestParseState, 'finish_request')
    @mock.patch.object(request.RequestParseState, 'finish_header')
    @mock.patch.object(request, 'Request', return_value='new_req')
    def test_start_request_finishes(self, mock_Request,
                                    mock_finish_header,
                                    mock_finish_request):
        state = request.RequestParseState()
        state._sequence = mock.Mock()
        state._header = 'header'
        state._request = 'request'

        state.start_request('filename', 'get', 'uri')

        self.assertEqual(state._request, 'new_req')
        mock_finish_request.assert_called_once_with('filename')
        mock_finish_header.assert_called_once_with('filename')
        mock_Request.assert_called_once_with(state._sequence, 'get', 'uri')
        state._sequence.push.assert_called_once_with('new_req')

    def test_finish_request(self):
        req = mock.Mock()
        state = request.RequestParseState()
        state._request = req

        state.finish_request('filename')

        req.fix.assert_called_once_with()
        self.assertEqual(state._request, None)

    @mock.patch.object(request.RequestParseState, 'finish_request')
    @mock.patch.object(request.RequestParseState, 'finish_header')
    @mock.patch.object(request, 'Gap', return_value='gap')
    def test_push_gap_bad_state(self, mock_Gap, mock_finish_header,
                                mock_finish_request):
        state = request.RequestParseState()
        state._header = 'header'
        state._request = 'request'

        self.assertRaises(request.RequestParseException, state.push_gap,
                          'filename', 12.34)

        self.assertFalse(mock_finish_request.called)
        self.assertFalse(mock_finish_header.called)
        self.assertFalse(mock_Gap.called)

    @mock.patch.object(request.RequestParseState, 'finish_request')
    @mock.patch.object(request.RequestParseState, 'finish_header')
    @mock.patch.object(request, 'Gap', return_value='gap')
    def test_push_gap(self, mock_Gap, mock_finish_header,
                      mock_finish_request):
        state = request.RequestParseState()
        state._sequence = mock.Mock()

        state.push_gap('filename', 12.34)

        self.assertEqual(state._request, None)
        self.assertFalse(mock_finish_request.called)
        self.assertFalse(mock_finish_header.called)
        mock_Gap.assert_called_once_with(12.34)
        state._sequence.push.assert_called_once_with('gap')

    @mock.patch.object(request.RequestParseState, 'finish_request')
    @mock.patch.object(request.RequestParseState, 'finish_header')
    @mock.patch.object(request, 'Gap', return_value='gap')
    def test_push_gap_finishes(self, mock_Gap, mock_finish_header,
                               mock_finish_request):
        state = request.RequestParseState()
        state._sequence = mock.Mock()
        state._header = 'header'
        state._request = 'request'

        state.push_gap('filename', 12.34)

        mock_finish_request.assert_called_once_with('filename')
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

    @mock.patch.object(request.RequestParseState, 'headers', {})
    def test_finish_header(self):
        header = mock.Mock()
        header.name = 'header'
        header.value = 'value'
        state = request.RequestParseState()
        state._header = header

        state.finish_header('filename')

        self.assertEqual(state.headers, dict(header='value'))

    @mock.patch.object(request.RequestParseState, 'headers',
                       dict(HEADER1='value1', HEADER2='value2'))
    @mock.patch.object(request.RequestParseState, 'finish_header')
    def test_delete_header(self, mock_finish_header):
        state = request.RequestParseState()

        state.delete_header('filename', 'header1')

        self.assertFalse(mock_finish_header.called)
        self.assertEqual(state.headers, dict(HEADER2='value2'))

    @mock.patch.object(request.RequestParseState, 'headers',
                       dict(HEADER2='value2'))
    @mock.patch.object(request.RequestParseState, 'finish_header')
    def test_delete_header_unset(self, mock_finish_header):
        state = request.RequestParseState()

        state.delete_header('filename', 'header1')

        self.assertFalse(mock_finish_header.called)
        self.assertEqual(state.headers, dict(HEADER2='value2'))

    @mock.patch.object(request.RequestParseState, 'headers',
                       dict(HEADER1='value1', HEADER2='value2'))
    @mock.patch.object(request.RequestParseState, 'finish_header')
    def test_delete_header_finish_header(self, mock_finish_header):
        state = request.RequestParseState()
        state._header = 'old_header'

        state.delete_header('filename', 'header1')

        mock_finish_header.assert_called_once_with('filename')
        self.assertEqual(state.headers, dict(HEADER2='value2'))

    @mock.patch.object(request.RequestParseState, 'headers', mock.Mock())
    @mock.patch.object(request.RequestParseState, 'finish_header')
    def test_reset_header(self, mock_finish_header):
        state = request.RequestParseState()

        state.reset_header('filename', 'header1')

        self.assertFalse(mock_finish_header.called)
        state.headers.reset.assert_called_once_with('HEADER1')

    @mock.patch.object(request.RequestParseState, 'headers', mock.Mock())
    @mock.patch.object(request.RequestParseState, 'finish_header')
    def test_reset_header_finish_header(self, mock_finish_header):
        state = request.RequestParseState()
        state._header = 'old_header'

        state.reset_header('filename', 'header1')

        mock_finish_header.assert_called_once_with('filename')
        state.headers.reset.assert_called_once_with('HEADER1')

    @mock.patch.object(request.RequestParseState, 'finish_request')
    @mock.patch.object(request.RequestParseState, 'finish_header')
    def test_finish(self, mock_finish_header, mock_finish_request):
        state = request.RequestParseState()
        state._sequence = 'sequence'

        state.finish('filename')

        self.assertFalse(mock_finish_request.called)
        self.assertFalse(mock_finish_header.called)
        self.assertEqual(state._sequence, None)
        self.assertEqual(state._request, None)
        self.assertEqual(state._header, None)

    @mock.patch.object(request.RequestParseState, 'finish_request')
    @mock.patch.object(request.RequestParseState, 'finish_header')
    def test_finish_finish_header(self, mock_finish_header,
                                  mock_finish_request):
        state = request.RequestParseState()
        state._sequence = 'sequence'
        state._request = 'request'
        state._header = 'header'

        state.finish('filename')

        mock_finish_request.assert_called_once_with('filename')
        mock_finish_header.assert_called_once_with('filename')
        self.assertEqual(state._sequence, None)
        self.assertEqual(state._request, None)
        self.assertEqual(state._header, None)

    def test_sequences(self):
        state = request.RequestParseState()
        state._sequences = dict(a=1, b=2, c=3)

        self.assertEqual(set(state.sequences), set([1, 2, 3]))

    def test_headers_request(self):
        state = request.RequestParseState()
        state._request = mock.Mock(headers='request')
        state._sequence = mock.Mock(headers='sequence')
        state._headers = 'global'

        self.assertEqual(state.headers, 'request')

    def test_headers_sequence(self):
        state = request.RequestParseState()
        state._sequence = mock.Mock(headers='sequence')
        state._headers = 'global'

        self.assertEqual(state.headers, 'sequence')

    def test_headers_global(self):
        state = request.RequestParseState()
        state._headers = 'global'

        self.assertEqual(state.headers, 'global')


class TestParseFile(unittest2.TestCase):
    def prep_data(self, mock_open, data):
        # A generator function to return lines from data
        def yield_lines():
            start = 0
            for idx, char in enumerate(data):
                if char == '\n':
                    yield data[start:idx + 1]
                    start = idx + 1

            if start < len(data):
                yield data[start:]

        # So it works as a context manager
        mock_open.return_value.__enter__.return_value = mock_open.return_value
        mock_open.return_value.__iter__.return_value = yield_lines()

    @mock.patch('__builtin__.open')
    def test_parse_file(self, mock_open):
        state = mock.Mock()
        self.prep_data(mock_open, """
# Comment in the left column (ignored)

   # Inline comment, header continuation (ignored)

global-header: partial value here#ignored comment marker
   continuation line # inline comment

[ sequence ] # sequence start

+12.34 # Trial gap

get /some/uri#fragment # introduce a request
""")

        request._parse_file(state, 'filename')

        mock_open.assert_called_once_with('filename')

        state.assert_has_calls([
            mock.call.start_header(
                'filename', 'global-header',
                'partial value here#ignored comment marker'),
            mock.call.extend_header('filename', 'continuation line'),
            mock.call.start_sequence('filename', 'sequence'),
            mock.call.push_gap('filename', 12.34),
            mock.call.start_request('filename', 'get', '/some/uri#fragment'),
            mock.call.finish('filename'),
        ])

    @mock.patch('__builtin__.open')
    def test_parse_file_bad_sequence_header(self, mock_open):
        state = mock.Mock()
        self.prep_data(mock_open, """
[bad_sequence
""")

        self.assertRaises(request.RequestParseException, request._parse_file,
                          state, 'filename')

    @mock.patch('__builtin__.open')
    def test_parse_file_bad_gap(self, mock_open):
        state = mock.Mock()
        self.prep_data(mock_open, """
+12.three
""")

        self.assertRaises(request.RequestParseException, request._parse_file,
                          state, 'filename')

    @mock.patch('__builtin__.open')
    def test_parse_file_bad_line(self, mock_open):
        state = mock.Mock()
        self.prep_data(mock_open, """
something
""")

        self.assertRaises(request.RequestParseException, request._parse_file,
                          state, 'filename')


class TestParseFiles(unittest2.TestCase):
    @mock.patch.object(request, 'RequestParseState',
                       return_value=mock.Mock(sequences='sequences'))
    @mock.patch.object(request, '_parse_file')
    def test_parse_files(self, mock_parse_file, mock_RequestParseState):
        result = request.parse_files(['file1', 'file2', 'file3'])

        self.assertEqual(result, 'sequences')
        mock_RequestParseState.assert_called_once_with()
        mock_parse_file.assert_has_calls([
            mock.call(mock_RequestParseState.return_value, 'file1'),
            mock.call(mock_RequestParseState.return_value, 'file2'),
            mock.call(mock_RequestParseState.return_value, 'file3'),
        ])
