# -*- coding: utf-8 -*-
# Copyright (c) 2018 the Pockets team, see AUTHORS.
# Licensed under the BSD License, see LICENSE for details.

"""Tests for :mod:`pockets.inspect` module."""

from __future__ import absolute_import
import sys
from functools import wraps

import pytest

import pockets
from pockets.decorators import classproperty
from pockets.inspect import collect_subclasses, collect_superclasses, \
    collect_superclass_attr_names, is_data, resolve, unwrap


class A(object):
    A_attr = 'A_attr'


class Z(object):
    Z_attr = 'Z_attr'


class B1(A):
    B1_attr = 'B1_attr'


class B2(A):
    B2_attr = 'B2_attr'


class C1(B1):
    C1_attr = 'C1_attr'


class C2(B1):
    C2_attr = 'C2_attr'


class C3(B2, Z):
    C3_attr = 'C3_attr'


class C4(B2, Z):
    C4_attr = 'C4_attr'


class TestCollectClasses(object):

    def test_collect_subclasses(self):
        assert set(collect_subclasses(A)) == set([B1, B2, C1, C2, C3, C4])
        assert set(collect_subclasses(Z)) == set([C3, C4])

    def test_collect_superclasses(self):
        assert set(collect_superclasses(C1)) == set([C1, B1, A, object])
        assert set(collect_superclasses(C3)) == set([C3, B2, A, Z, object])

    def test_collect_superclasses_terminal_class(self):
        assert set(collect_superclasses(C1, terminal_class=object)) == \
            set([C1, B1, A])
        assert set(collect_superclasses(C1, terminal_class=A)) == \
            set([C1, B1])
        assert set(collect_superclasses(C1, terminal_class=B1)) == \
            set([C1])
        assert set(collect_superclasses(C3, terminal_class=A)) == \
            set([C3, B2, Z, object])
        assert set(collect_superclasses(C3, terminal_class=[A, object])) == \
            set([C3, B2, Z])

    def test_collect_superclasses_modules(self):
        mod = sys.modules['tests.test_inspect']
        assert set(collect_superclasses(C1, modules=mod)) == \
            set([C1, B1, A])
        assert set(collect_superclasses(C1, modules='tests.test_inspect')) == \
            set([C1, B1, A])
        assert set(collect_superclasses(C1, modules=[mod, 'NOTFOUND'])) == \
            set([C1, B1, A])
        assert set(collect_superclasses(C1, modules='tests')) == set()
        assert set(collect_superclasses(C1, modules='tests.NOTFOUND')) == set()
        assert set(collect_superclasses(C1, modules='NOTFOUND')) == set()

    def test_collect_superclass_attr_names(self):
        result = collect_superclass_attr_names(C1)
        assert set(filter(lambda s: not s.startswith('_'), result)) == set([
            'A_attr',
            'B1_attr',
            'C1_attr'])
        result = collect_superclass_attr_names(C3)
        assert set(filter(lambda s: not s.startswith('_'), result)) == set([
            'A_attr',
            'B2_attr',
            'C3_attr',
            'Z_attr'])


class TestIsData(object):

    class DocClass(object):
        """is not data"""
        clsattr = 'is data'

        def __init__(self):
            self.attr = 'is data'

        @classproperty
        def clsprop(cls):
            """is data"""
            pass

        @classmethod
        def clsmeth(cls):
            """is not data"""
            pass

        @property
        def prop(self):
            """is not data"""
            pass

        def meth(self):
            """is not data"""
            pass

    def test_is_data(self):
        assert is_data('string literal')
        assert is_data(TestIsData.DocClass)
        assert is_data(TestIsData.DocClass.clsattr)
        assert is_data(TestIsData.DocClass.clsprop)
        assert not is_data(TestIsData.DocClass.prop)
        assert not is_data(TestIsData.DocClass.meth)
        assert not is_data(TestIsData.DocClass.clsmeth)
        docobj = TestIsData.DocClass()
        assert is_data(docobj)
        assert is_data(docobj.attr)
        assert is_data(docobj.clsattr)
        assert is_data(docobj.prop)
        assert not is_data(docobj.meth)
        assert not is_data(docobj.clsmeth)


class TestResolve(object):
    def test_none(self):
        assert resolve(None) is None

    def test_object(self):
        x = object()
        assert resolve(x) is x
        assert resolve(x, 'pockets') is x
        assert resolve(x, ['pockets']) is x
        assert resolve(x, ['pockets', 're']) is x

    def test_local_module(self):
        assert resolve('TestResolve') is self.__class__
        assert resolve('TestResolve', 'tests.test_inspect') is self.__class__
        pytest.raises(ValueError, resolve, 'TestResolve', 'pockets')

    def test_modules_none(self):
        assert resolve('pockets') is pockets
        assert resolve('pockets.iterators') is pockets.iterators
        assert resolve('pockets.iterators.iterpeek') is \
            pockets.iterators.iterpeek

    def test_modules_string(self):
        sock = __import__('socket')
        assert resolve('socket') is sock
        assert resolve('getfqdn', 'socket') is sock.getfqdn
        assert resolve('iterators', 'pockets') is pockets.iterators
        assert resolve('iterpeek', 'pockets.iterators') is \
            pockets.iterators.iterpeek
        assert resolve('iterators.iterpeek', 'pockets') is \
            pockets.iterators.iterpeek

    def test_modules_list(self):
        sock = __import__('socket')
        assert resolve('socket') is sock
        assert resolve('getfqdn', ['pockets', 'socket']) is sock.getfqdn
        assert resolve('iterators', ['pockets', 'socket']) is \
            pockets.iterators
        assert resolve('iterators', ['socket', 'pockets']) is \
            pockets.iterators
        assert resolve('iterpeek', ['pockets', 'pockets.iterators']) is \
            pockets.iterators.iterpeek
        assert resolve('iterpeek', ['pockets.iterators', 'pockets']) is \
            pockets.iterators.iterpeek
        assert resolve(
            'iterators.iterpeek', ['pockets', 'pockets.iterators']) is \
            pockets.iterators.iterpeek
        assert resolve(
            'iterators.iterpeek', ['pockets.iterators', 'pockets']) is \
            pockets.iterators.iterpeek

    def test_relative_import(self):
        sock = __import__('socket')
        assert resolve('.socket') is sock
        assert resolve('..socket') is sock
        assert resolve('.getfqdn', 'socket') is sock.getfqdn
        assert resolve('..getfqdn', 'socket') is sock.getfqdn
        assert resolve('.iterators', 'pockets') is pockets.iterators
        assert resolve('..iterators', 'pockets') is pockets.iterators
        assert resolve('.iterpeek', 'pockets.iterators') is \
            pockets.iterators.iterpeek
        assert resolve('..iterpeek', 'pockets.iterators') is \
            pockets.iterators.iterpeek
        assert resolve('.iterators.iterpeek', 'pockets') is \
            pockets.iterators.iterpeek
        assert resolve('..iterators.iterpeek', 'pockets') is \
            pockets.iterators.iterpeek

        mod = sys.modules['tests.test_inspect']
        mod.MOD_ATTR = 'asdf'
        assert resolve('MOD_ATTR') == 'asdf'
        assert resolve('.MOD_ATTR') == 'asdf'

        # Seems odd that this would raise an error, seeing as it worked
        # fine two lines above. However, resolve uses the *calling* function's
        # module as the search path, which in this case is pytest
        pytest.raises(ValueError, resolve, 'MOD_ATTR')
        pytest.raises(ValueError, resolve, '.MOD_ATTR')

        re_mod = __import__('re')
        mod.re = 'zxcv'
        assert resolve('re') is re_mod
        assert resolve('.re') == 'zxcv'
        assert resolve('..re') is re_mod
        assert resolve('...re') is re_mod
        assert resolve('re', 'tests.test_inspect') == 'zxcv'
        assert resolve('.re', 'tests.test_inspect') == 'zxcv'
        assert resolve('..re', 'tests.test_inspect') == 'zxcv'
        assert resolve('test_inspect.re', 'tests') == 'zxcv'
        assert resolve('.test_inspect.re', 'tests') == 'zxcv'
        assert resolve('..test_inspect.re', 'tests') == 'zxcv'

    def test_raises(self):
        pytest.raises(ValueError, resolve, 'NOTFOUND')
        pytest.raises(ValueError, resolve, 'pockets.NOTFOUND')
        pytest.raises(ValueError, resolve, 'NOTFOUND', 'pockets')
        pytest.raises(ValueError, resolve, 'NOTFOUND', ['pockets'])
        pytest.raises(ValueError, resolve, 'NOTFOUND', ['pockets', 're'])


def wraps_decorator(func):
    @wraps(func)
    def with_wraps_decorator(*args, **kwargs):
        return func(*args, **kwargs)

    if not hasattr(with_wraps_decorator, '__wrapped__'):
        with_wraps_decorator.__wrapped__ = func

    return with_wraps_decorator


class TestUnwrap(object):

    def test_never_wrapped(self):
        def innermost():
            return 'return value'

        unwrapped = unwrap(innermost)
        assert unwrapped is innermost

    def test_single_wrapped(self):
        def innermost():
            return 'return value'

        wrapped = wraps_decorator(innermost)
        assert wrapped is not innermost
        assert wrapped() == 'return value'

        unwrapped = unwrap(wrapped)
        assert unwrapped is innermost

    def test_multi_wrapped(self):
        def innermost():
            return 'return value'

        wrapped = wraps_decorator(wraps_decorator(wraps_decorator(innermost)))
        assert wrapped is not innermost
        assert wrapped() == 'return value'

        unwrapped = unwrap(wrapped)
        assert unwrapped is innermost
