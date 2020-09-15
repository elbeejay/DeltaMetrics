import pytest

import sys
import os

import numpy as np
import matplotlib.pyplot as plt

from deltametrics import utils


class TestNoStratigraphyError:

    def test_needs_obj_argument(self):
        with pytest.raises(TypeError):
            raise utils.NoStratigraphyError()

    def test_only_obj_argument(self):
        _mtch = "'str' object has no*."
        with pytest.raises(utils.NoStratigraphyError, match=_mtch):
            raise utils.NoStratigraphyError('someobj')

    def test_obj_and_var(self):
        _mtch = "'str' object has no attribute 'somevar'."
        with pytest.raises(utils.NoStratigraphyError, match=_mtch):
            raise utils.NoStratigraphyError('someobj', 'somevar')


def test_format_number_float():
    _val = float(5.2)
    _fnum = utils.format_number(_val)
    assert _fnum == '10'

    _val = float(50.2)
    _fnum = utils.format_number(_val)
    assert _fnum == '50'

    _val = float(15.0)
    _fnum = utils.format_number(_val)
    assert _fnum == '20'


def test_format_number_int():
    _val = int(5)
    _fnum = utils.format_number(_val)
    assert _fnum == '0'

    _val = int(6)
    _fnum = utils.format_number(_val)
    assert _fnum == '10'

    _val = int(52)
    _fnum = utils.format_number(_val)
    assert _fnum == '50'

    _val = int(15)
    _fnum = utils.format_number(_val)
    assert _fnum == '20'


def test_format_table_float():
    _val = float(5.2)
    _fnum = utils.format_table(_val)
    assert _fnum == '5.2'

    _val = float(50.2)
    _fnum = utils.format_table(_val)
    assert _fnum == '50.2'

    _val = float(15.0)
    _fnum = utils.format_table(_val)
    assert _fnum == '15.0'

    _val = float(15.03689)
    _fnum = utils.format_table(_val)
    assert _fnum == '15.0'

    _val = float(15.0689)
    _fnum = utils.format_table(_val)
    assert _fnum == '15.1'

def test_format_table_float():
    _val = int(5)
    _fnum = utils.format_table(_val)
    assert _fnum == '5'

    _val = int(5.8)
    _fnum = utils.format_table(_val)
    assert _fnum == '5'

    _val = int(5.2)
    _fnum = utils.format_table(_val)
    assert _fnum == '5'
