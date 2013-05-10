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
