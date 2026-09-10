import collections
import collections.abc
import gc
import pickle
import random
import re
import string
import sys
import types
import unittest
import weakref
from test import support
from test.support import import_helper


class CustomHash:
    def __init__(self, hash):
        self.hash = hash
    def __hash__(self):
        return self.hash
    def __repr__(self):
        return f'<CustomHash {self.hash} at {id(self):#x}>'


class DictTest(unittest.TestCase):

    def test_invalid_keyword_arguments(self):
        class Custom(dict):
            pass
        for invalid in {1 : 2}, Custom({1 : 2}):
            with self.assertRaises(TypeError):
                dict(**invalid)
            with self.assertRaises(TypeError):
                {}.update(**invalid)

    def test_constructor(self):
        # calling built-in types without argument must return empty
        self.assertEqual(dict(), {})
        self.assertIsNot(dict(), {})

    def test_literal_constructor(self):
        # check literal constructor for different sized dicts
        # (to exercise the BUILD_MAP oparg).
        for n in (0, 1, 6, 256, 400):
            items = [(''.join(random.sample(string.ascii_letters, 8)), i)
                     for i in range(n)]
            random.shuffle(items)
            formatted_items = ('{!r}: {:d}'.format(k, v) for k, v in items)
            dictliteral = '{' + ', '.join(formatted_items) + '}'
            self.assertEqual(eval(dictliteral), dict(items))

    def test_merge_operator(self):

        a = {0: 0, 1: 1, 2: 1}
        b = {1: 1, 2: 2, 3: 3}

        c = a.copy()
        c |= b

        self.assertEqual(a | b, {0: 0, 1: 1, 2: 2, 3: 3})
        self.assertEqual(c, {0: 0, 1: 1, 2: 2, 3: 3})

        c = b.copy()
        c |= a

        self.assertEqual(b | a, {1: 1, 2: 1, 3: 3, 0: 0})
        self.assertEqual(c, {1: 1, 2: 1, 3: 3, 0: 0})

        c = a.copy()
        c |= [(1, 1), (2, 2), (3, 3)]

        self.assertEqual(c, {0: 0, 1: 1, 2: 2, 3: 3})

        self.assertIs(a.__or__(None), NotImplemented)
        self.assertIs(a.__or__(()), NotImplemented)
        self.assertIs(a.__or__("BAD"), NotImplemented)
        self.assertIs(a.__or__(""), NotImplemented)

        self.assertRaises(TypeError, a.__ior__, None)
        self.assertEqual(a.__ior__(()), {0: 0, 1: 1, 2: 1})
        self.assertRaises(ValueError, a.__ior__, "BAD")
        self.assertEqual(a.__ior__(""), {0: 0, 1: 1, 2: 1})

    def test_bool(self):
        self.assertIs(not {}, True)
        self.assertTrue({1: 2})
        self.assertIs(bool({}), False)
        self.assertIs(bool({1: 2}), True)

    def test_keys(self):
        d = {}
        self.assertEqual(set(d.keys()), set())
        d = {'a': 1, 'b': 2}
        k = d.keys()
        self.assertEqual(set(k), {'a', 'b'})
        self.assertIn('a', k)
        self.assertIn('b', k)
        self.assertIn('a', d)
        self.assertIn('b', d)
        self.assertRaises(TypeError, d.keys, None)
        self.assertEqual(repr(dict(a=1).keys()), "dict_keys(['a'])")

    def test_values(self):
        d = {}
        self.assertEqual(set(d.values()), set())
        d = {1:2}
        self.assertEqual(set(d.values()), {2})
        self.assertRaises(TypeError, d.values, None)
        self.assertEqual(repr(dict(a=1).values()), "dict_values([1])")

    def test_items(self):
        d = {}
        self.assertEqual(set(d.items()), set())

        d = {1:2}
        self.assertEqual(set(d.items()), {(1, 2)})
        self.assertRaises(TypeError, d.items, None)
        self.assertEqual(repr(dict(a=1).items()), "dict_items([('a', 1)])")

    def test_views_mapping(self):
        mappingproxy = type(type.__dict__)
        class Dict(dict):
            pass
        for cls in [dict, Dict]:
            d = cls()
            m1 = d.keys().mapping
            m2 = d.values().mapping
            m3 = d.items().mapping

            for m in [m1, m2, m3]:
                self.assertIsInstance(m, mappingproxy)
                self.assertEqual(m, d)

            d["foo"] = "bar"

            for m in [m1, m2, m3]:
                self.assertIsInstance(m, mappingproxy)
                self.assertEqual(m, d)

    def test_contains(self):
        d = {}
        self.assertNotIn('a', d)
        self.assertFalse('a' in d)
        self.assertTrue('a' not in d)
        d = {'a': 1, 'b': 2}
        self.assertIn('a', d)
        self.assertIn('b', d)
        self.assertNotIn('c', d)

        self.assertRaises(TypeError, d.__contains__)

    def test_len(self):
        d = {}
        self.assertEqual(len(d), 0)
        d = {'a': 1, 'b': 2}
        self.assertEqual(len(d), 2)

    def test_getitem(self):
        d = {'a': 1, 'b': 2}
        self.assertEqual(d['a'], 1)
        self.assertEqual(d['b'], 2)
        d['c'] = 3
        d['a'] = 4
        self.assertEqual(d['c'], 3)
        self.assertEqual(d['a'], 4)
        del d['b']
        self.assertEqual(d, {'a': 4, 'c': 3})

        self.assertRaises(TypeError, d.__getitem__)

        class BadEq(object):
            def __eq__(self, other):
                raise Exc()
            def __hash__(self):
                return 24

        d = {}
        d[BadEq()] = 42
        self.assertRaises(KeyError, d.__getitem__, 23)

        class Exc(Exception): pass

        class BadHash(object):
            fail = False
            def __hash__(self):
                if self.fail:
                    raise Exc()
                else:
                    return 42

        x = BadHash()
        d[x] = 42
        x.fail = True
        self.assertRaises(Exc, d.__getitem__, x)

    def test_clear(self):
        d = {1:1, 2:2, 3:3}
        d.clear()
        self.assertEqual(d, {})

        self.assertRaises(TypeError, d.clear, None)

    def test_update(self):
        d = {}
        d.update({1:100})
        d.update({2:20})
        d.update({1:1, 2:2, 3:3})
        self.assertEqual(d, {1:1, 2:2, 3:3})

        d.update()
        self.assertEqual(d, {1:1, 2:2, 3:3})

        self.assertRaises((TypeError, AttributeError), d.update, None)

        class SimpleUserDict:
            def __init__(self):
                self.d = {1:1, 2:2, 3:3}
            def keys(self):
                return self.d.keys()
            def __getitem__(self, i):
                return self.d[i]
        d.clear()
        d.update(SimpleUserDict())
        self.assertEqual(d, {1:1, 2:2, 3:3})

        class Exc(Exception): pass

        d.clear()
        class FailingUserDict:
            def keys(self):
                raise Exc
        self.assertRaises(Exc, d.update, FailingUserDict())

        class FailingUserDict:
            def keys(self):
                class BogonIter:
                    def __init__(self):
                        self.i = 1
                    def __iter__(self):
                        return self
                    def __next__(self):
                        if self.i:
                            self.i = 0
                            return 'a'
                        raise Exc
                return BogonIter()
            def __getitem__(self, key):
                return key
        self.assertRaises(Exc, d.update, FailingUserDict())

        class FailingUserDict:
            def keys(self):
                class BogonIter:
                    def __init__(self):
                        self.i = ord('a')
                    def __iter__(self):
                        return self
                    def __next__(self):
                        if self.i <= ord('z'):
                            rtn = chr(self.i)
                            self.i += 1
                            return rtn
                        raise StopIteration
                return BogonIter()
            def __getitem__(self, key):
                raise Exc
        self.assertRaises(Exc, d.update, FailingUserDict())

        class badseq(object):
            def __iter__(self):
                return self
            def __next__(self):
                raise Exc()

        self.assertRaises(Exc, {}.update, badseq())

        self.assertRaises(ValueError, {}.update, [(1, 2, 3)])

        # gh-157217: merging from a mappingproxy wrapping a dict should
        # succeed (and on the free-threaded build, take the locked path).
        d.clear()
        d.update(types.MappingProxyType({1: 1, 2: 2, 3: 3}))
        self.assertEqual(d, {1: 1, 2: 2, 3: 3})
        self.assertEqual(dict(types.MappingProxyType({'a': 1, 'b': 2})),
                         {'a': 1, 'b': 2})
        self.assertEqual(dict(types.MappingProxyType(collections.UserDict(x=1))),
                         {'x': 1})

    def test_update_type_error(self):
        with self.assertRaises(TypeError) as cm:
            {}.update([object() for _ in range(3)])

        self.assertEqual(str(cm.exception), "object is not iterable")
        self.assertEqual(
            cm.exception.__notes__,
            ['Cannot convert dictionary update sequence element #0 to a sequence'],
        )

        def badgen():
            yield "key"
            raise TypeError("oops")
            yield "value"

        with self.assertRaises(TypeError) as cm:
            dict([badgen() for _ in range(3)])

        self.assertEqual(str(cm.exception), "oops")
        self.assertEqual(
            cm.exception.__notes__,
            ['Cannot convert dictionary update sequence element #0 to a sequence'],
        )
