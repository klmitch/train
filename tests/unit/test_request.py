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
