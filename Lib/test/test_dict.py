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
        self.assertEqual(dict(), {})
        self.assertIsNot(dict(), {})
