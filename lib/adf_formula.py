"""Safe evaluation of variable-derivation formulas for the ADF.

A derived variable may specify a ``derivation_formula`` string in
``adf_variable_defaults.yaml`` alongside its ``derivable_from`` list, e.g.::

    RESTOM:
      derivable_from: [FSNT, FLNT]
      derivation_formula: "FSNT - FLNT"

    cb_SULFATE:
      derivable_from: [so4_a1, so4_a2, so4_a3]
      derivation_formula: "so4_a1 + so4_a2 + so4_a3"

The formula is evaluated by :func:`safe_eval` against a namespace built from
the constituent variables (as ``xarray.DataArray`` objects).  Only ``np``,
``xr``, and the supplied constituent names are exposed; Python builtins are
blocked.  Variables that do NOT define a ``derivation_formula`` fall back to the
default derivation (sum of constituents), so this is fully backward compatible.

Adapted from cmip7-prep's ``mapping_compat._safe_eval`` (the land/PFT-specific
helpers were removed; add atmosphere-specific helpers here as needed).

Security note
------------
Formulas are *trusted* content from the repo-controlled variable-defaults file,
NOT runtime user input.  ``eval`` with an empty ``__builtins__`` blocks casual
misuse, but it is **not** a hardened sandbox against a deliberately malicious
expression.  Do not evaluate untrusted formula strings with this function.
"""

import numpy as np
import xarray as xr


def safe_eval(expr, local_names):
    """Evaluate a derivation-formula string in a restricted namespace.

    Parameters
    ----------
    expr : str
        Arithmetic / xarray expression, e.g. ``"PRECC + PRECL"`` or
        ``"FSNT - FLNT"``.  Tokens must be keys in ``local_names`` (or ``np`` /
        ``xr``).
    local_names : dict
        Mapping of token name -> value (typically ``xarray.DataArray``) that the
        expression may reference.

    Returns
    -------
    xarray.DataArray (usually) or scalar
        Result of evaluating the expression.

    Examples
    --------
    >>> safe_eval("x + 2", {"x": 3})
    5
    """
    # Block all Python builtins (no __import__, open, etc.).
    safe_globals = {"__builtins__": {}}

    # Expose numpy / xarray plus the caller-supplied constituent DataArrays.
    safe_locals = dict(local_names)
    safe_locals.update({"np": np, "xr": xr})

    # pylint: disable=eval-used
    return eval(expr, safe_globals, safe_locals)
