#!/usr/bin/python
'''
Priority queue with random access updates
-----------------------------------------

.. autoclass:: PrioQueue
   :members:
   :special-members:

'''
#-----------------------------------------------------------------------------

class PrioQueue:
    '''
    Priority queue that supports updating priority of arbitrary elements and
    removing arbitrary elements.

    Entry with lowest priority value is returned first.

    Mutation operations (:meth:`set()`, :meth:`pop()`, :meth:`remove()`, and
    :meth:`update()`) have complexity of ``O(log(n))``. Read operations
    (:meth:`length()` and :meth:`peek()`) have complexity of ``O(1)``.
    '''
    #-------------------------------------------------------
    # element container {{{

    class _Element:
        def __init__(self, prio, entry, pos, key):
            self.prio = prio
            self.entry = entry
            self.pos = pos
            self.key = key

        def __cmp__(self, other):
            return cmp(self.prio, other.prio) or \
                   cmp(id(self.entry), id(other.entry))

    # }}}
    #-------------------------------------------------------

    def __init__(self, make_key = None):
        '''
        :param make_key: element-to-hashable converter function

        If :obj:`make_key` is left unspecified, an identity function is used
        (which means that the queue can only hold hashable objects).
        '''
        # children: (2 * i + 1), (2 * i + 2)
        # parent: (i - 1) / 2
        self._heap = []
        self._keys = {}
        if make_key is not None:
            self._make_key = make_key
        else:
            self._make_key = lambda x: x

    #-------------------------------------------------------
    # dict-like operations {{{

    def __len__(self):
        '''
        :return: queue length

        Return length of the queue.
        '''
        return len(self._heap)

    def __contains__(self, entry):
        '''
        :param entry: entry to check
        :return: ``True`` if :obj:`entry` is in queue, ``False`` otherwise

        Check whether the queue contains an entry.
        '''
        return (self._make_key(entry) in self._keys)

    def __setitem__(self, entry, priority):
        '''
        :param entry: entry to add/update
        :param priority: entry's priority

        Set priority for an entry, either by adding a new or updating an
        existing one.
        '''
        self.set(entry, priority)

    def __getitem__(self, entry):
        '''
        :param entry: entry to get priority of
        :return: priority
        :throws: :exc:`KeyError` if entry is not in the queue

        Get priority of an entry.
        '''
        key = self._make_key(entry)
        return self._keys[key].prio # NOTE: allow the KeyError to propagate

    def __delitem__(self, entry):
        '''
        :param entry: entry to remove

        Remove an entry from the queue.
        '''
        self.remove(entry)

    # }}}
    #-------------------------------------------------------
    # main operations {{{

    def __iter__(self):
        '''
        :return: iterator

        Iterate over the entries in the queue.

        Order of the entries is unspecified.
        '''
        for element in self._heap:
            yield element.entry

    def iterentries(self):
        '''
        :return: iterator

        Iterate over the entries in the queue.

        Order of the entries is unspecified.
        '''
        for element in self._heap:
            yield element.entry

    def entries(self):
        '''
        :return: list of entries

        Retrieve list of entries stored in the queue.

        Order of the entries is unspecified.
        '''
        return [e.entry for e in self._heap]

    def length(self):
        '''
        :return: queue length

        Return length of the queue.
        '''
        return len(self._heap)

    def set(self, entry, priority):
        '''
        :param entry: entry to add/update
        :param priority: entry's priority

        Set priority for an entry, either by adding a new or updating an
        existing one.
        '''
        key = self._make_key(entry)
        if key not in self._keys:
            element = PrioQueue._Element(priority, entry, len(self._heap), key)
            self._keys[key] = element
            self._heap.append(element)
        else:
            element = self._keys[key]
            element.prio = priority
        self._heapify(element.pos)

    def pop(self):
        '''
        :return: tuple ``(priority, entry)``
        :throws: :exc:`IndexError` when the queue is empty

        Return the entry with lowest priority value. The entry is immediately
        removed from the queue.
        '''
        if len(self._heap) == 0:
            raise IndexError("queue is empty")
        element = self._heap[0]
        del self._keys[element.key]
        if len(self._heap) > 1:
            self._heap[0] = self._heap.pop()
            self._heap[0].pos = 0
            self._heapify_downwards(0)
        else:
            # this was the last element in the queue
            self._heap.pop()
        return (element.prio, element.entry)

    def peek(self):
        '''
        :return: tuple ``(priority, entry)``
        :throws: :exc:`IndexError` when the queue is empty

        Return the entry with lowest priority value. The entry is not removed
        from the queue.
        '''
        if len(self._heap) == 0:
            raise IndexError("queue is empty")
        return (self._heap[0].prio, self._heap[0].entry)

    def remove(self, entry):
        '''
        :return: priority of :obj:`entry` or ``None`` when :obj:`entry` was
            not found

        Remove an arbitrary entry from the queue.
        '''
        key = self._make_key(entry)
        if key not in self._keys:
            return None
        element = self._keys.pop(key)
        if element.pos < len(self._heap) - 1:
            # somewhere in the middle of the queue
            self._heap[element.pos] = self._heap.pop()
            self._heap[element.pos].pos = element.pos
            self._heapify(element.pos)
        else:
            # this was the last element in the queue
            self._heap.pop()
        return element.prio

    def update(self, entry, priority):
        '''
        :param entry: entry to update
        :param priority: entry's new priority
        :return: old priority of the entry
        :throws: :exc:`KeyError` if entry is not in the queue

        Update priority of an arbitrary entry.
        '''
        key = self._make_key(entry)
        element = self._keys[key] # NOTE: allow the KeyError to propagate
        old_priority = element.prio
        element.prio = priority
        self._heapify(element.pos)
        return old_priority

    # }}}
    #-------------------------------------------------------
    # maintain heap property {{{

    def _heapify(self, i):
        if i > 0 and self._heap[i] < self._heap[(i - 1) / 2]:
            self._heapify_upwards(i)
        else:
            self._heapify_downwards(i)

    def _heapify_upwards(self, i):
        p = (i - 1) / 2 # parent index
        while p >= 0 and self._heap[i] < self._heap[p]:
            # swap element and its parent
            (self._heap[i], self._heap[p]) = (self._heap[p], self._heap[i])
            # update positions of the elements
            self._heap[i].pos = i
            self._heap[p].pos = p
            # now check if the parent node satisfies heap property
            i = p
            p = (i - 1) / 2

    def _heapify_downwards(self, i):
        c = 2 * i + 1 # children: (2 * i + 1), (2 * i + 2)
        while c < len(self._heap):
            # select the smaller child (if the other child exists)
            if c + 1 < len(self._heap) and self._heap[c + 1] < self._heap[c]:
                c += 1
            if self._heap[i] < self._heap[c]:
                # heap property satisfied, nothing left to do
                return
            # swap element and its smaller child
            (self._heap[i], self._heap[c]) = (self._heap[c], self._heap[i])
            # update positions of the elements
            self._heap[i].pos = i
            self._heap[c].pos = c
            # now check if the smaller child satisfies heap property
            i = c
            c = 2 * i + 1

    # }}}
    #-------------------------------------------------------

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
