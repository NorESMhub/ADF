"""
Collection of python unit tests for the `adf_formula` module
(safe evaluation of variable-derivation formulas).
"""

#+++++++++++++++++++++++
#Import required modules
#+++++++++++++++++++++++

import unittest
import sys
import os
import os.path

#Set relevant path variables:
_CURRDIR = os.path.abspath(os.path.dirname(__file__))
_ADF_LIB_DIR = os.path.join(_CURRDIR, os.pardir, os.pardir)

#Add ADF "lib" directory to python path:
sys.path.append(_ADF_LIB_DIR)

import numpy as np
import xarray as xr

#Import the module under test:
from adf_formula import safe_eval


#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#Main adf_formula testing routine, used when script is run directly
#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

class AdfFormulaTestRoutine(unittest.TestCase):

    """Tests for adf_formula.safe_eval."""

    @staticmethod
    def _da(values):
        """Helper: build a 1-D float DataArray."""
        return xr.DataArray(np.array(values, dtype=float), dims="x")

    def test_sum_of_constituents(self):
        """Default-style derivation: sum of two constituents."""
        con_a = self._da([1, 2, 3])
        con_b = self._da([10, 20, 30])
        result = safe_eval("A + B", {"A": con_a, "B": con_b})
        self.assertIsInstance(result, xr.DataArray)
        np.testing.assert_array_equal(result.values, [11, 22, 33])

    def test_difference(self):
        """RESTOM-style derivation: FSNT - FLNT."""
        fsnt = self._da([100, 200, 300])
        flnt = self._da([40, 50, 60])
        result = safe_eval("FSNT - FLNT", {"FSNT": fsnt, "FLNT": flnt})
        np.testing.assert_array_equal(result.values, [60, 150, 240])

    def test_numpy_available(self):
        """`np` is exposed in the namespace."""
        arr = self._da([1, 2, 3, 4])
        result = safe_eval("np.mean(x)", {"x": arr})
        self.assertAlmostEqual(float(result), 2.5)

    def test_scalar_expression(self):
        """Non-DataArray (scalar) expressions still evaluate."""
        self.assertEqual(safe_eval("x + 2", {"x": 3}), 5)

    def test_builtins_are_blocked(self):
        """Python builtins (e.g. __import__) must not be accessible."""
        with self.assertRaises(Exception):
            safe_eval("__import__('os').getcwd()", {})

    def test_undefined_token_raises(self):
        """A token not supplied (and not np/xr) raises NameError."""
        with self.assertRaises(NameError):
            safe_eval("A + B", {"A": self._da([1, 2])})  # B is undefined


#++++++++++++++++++
#Run tests directly
#++++++++++++++++++

if __name__ == "__main__":
    unittest.main()
