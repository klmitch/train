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

import collections


# A sentinel used to signal that an argument was not passed in
_unpassed = object()


class StackedDict(collections.MutableMapping):
    """
    Represent a dictionary "stacked" on top of another dictionary;
    that is, keys in the parent dictionary appear to exist in this
    dictionary.  Modifications to values in this dictionary do not
    update the parent dictionary.  Keys may be set to other values, or
    even deleted; to reset a key to the value found in the parent, use
    the ``reset()`` method.  To convert this to a regular dictionary
    that is no longer stacked on its parents, replace the value with
    the result of the ``copy()`` method.
    """

    def __init__(self, parent=None):
        """
        Initialize a ``StackedDict`` object.

        :param parent: The parent dictionary, if any.
        """

        self._parent = parent
        self._deleted = set()
        self._values = {}

    def __getitem__(self, key):
        """
        Retrieve the value of the specified key.

        :param key: The desired key.

        :returns: The value of the key.
        """

        # Has the key been deleted?
        if key in self._deleted:
            raise KeyError(key)

        # OK, try sucking it out of our stored values
        if key in self._values:
            return self._values[key]

        # No place else to search if we have no parent
        if not self._parent:
            raise KeyError(key)

        # Get the key from the parent...
        return self._parent[key]

    def __setitem__(self, key, value):
        """
        Set the value of the specified key.

        :param key: The desired key.
        :param value: The new value for the key.
        """

        # Set the value
        self._values[key] = value

        # Also drop it from the set of deleted keys...
        self._deleted.discard(key)

    def __delitem__(self, key):
        """
        Delete the specified key.  After this, calling
        ``__getitem__()`` on the same key will raise a ``KeyError``,
        even if the key exists in the parent.

        :param key: The desired key.
        """

        # Has the key already been deleted?
        if key in self._deleted:
            raise KeyError(key)

        # If we have a local override, delete that; otherwise, verify
        # it exists in the parent (if we have one)
        if key in self._values:
            del self._values[key]
        elif not self._parent or key not in self._parent:
            raise KeyError(key)

        # Add the key to the deleted set
        self._deleted.add(key)

    def __iter__(self):
        """
        Return an iterator that will iterate over all the keys in the
        dictionary.  This will include keys in the parent that have
        not been explicitly deleted from this dictionary.
        """

        # First, yield all our local keys
        keys = set()
        for key in self._values:
            keys.add(key)
            yield key

        # If we don't have a parent, we're done
        if not self._parent:
            return

        # Now traverse the parent
        for key in self._parent:
            # Skip keys we covered above or that have been deleted...
            if key in keys or key in self._deleted:
                continue

            keys.add(key)
            yield key

    def __len__(self):
        """
        Return the number of elements in the dictionary.  This will
        count all the elements in the parent as if they were elements
        of this dictionary.
        """

        return len(list(iter(self)))

    def reset(self, key=_unpassed):
        """
        Reset a key override.  Any overrides applied to the specified
        key will be removed, allowing the value in the parent to be
        seen again.

        :param key: The key to reset.  If not provided, all keys will
                    be reset.
        """

        if key is _unpassed:
            # OK, clear everything
            self._deleted = set()
            self._values = {}
        else:
            # Clear just the one key
            self._deleted.discard(key)
            if key in self._values:
                del self._values[key]

    def copy(self):
        """
        Return a plain dictionary copy of this object.  Changes in
        this dictionary or in the parent will not be reflected in the
        returned dictionary.
        """

        return dict(self.iteritems())
