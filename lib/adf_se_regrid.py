"""Spectral-element (SE) -> lat/lon regridding for the atmosphere (CAM) realm.

Provides an xESMF-based regridder built from a pre-generated ESMF
weight file, and a routine that regrids all `ncol`-carrying variables
of a CAM dataset to a regular lat/lon grid while preserving the
non-horizontal pass-through variables (hyam/hybm/hyai/hybi/P0,
lev/ilev, time_bnds, gw, ...) and attributes that xESMF otherwise
drops.

"""

import numpy as np
import xarray as xr
import xesmf


def _restore_passthrough_and_attrs(ds_out, ds_in, horiz_dim):
    """Restore variables, coords and attrs that xESMF drops during regridding.

    xESMF only emits variables that carry the horizontal regridding dims;
    everything else (time_bnds, hyam/hybm/hyai/hybi, P0, lev/ilev, gw, scalar
    reference values, ...) is dropped, and in older xESMF versions the
    per-variable and global attrs are lost too.  Copy them back from ds_in.
    """
    # Restore global (dataset-level) attrs
    ds_out.attrs = dict(ds_in.attrs)

    # Restore per-variable attrs/encoding on regridded variables
    for name in ds_out.variables:
        if name in ds_in.variables:
            if not ds_out[name].attrs:
                ds_out[name].attrs = dict(ds_in[name].attrs)
            if not ds_out[name].encoding:
                ds_out[name].encoding = dict(ds_in[name].encoding)

    # Add back any pass-through variables that don't carry the horiz dim
    for name in ds_in.variables:
        if name in ds_out.variables:
            continue
        if horiz_dim in ds_in[name].dims:
            # had the horiz dim but didn't survive regridding -- skip
            continue
        ds_out[name] = ds_in[name]

    return ds_out


def make_se_regridder(weight_file, regrid_method="conserved"):
    """Build an xESMF Regridder from a pre-generated ESMF weight (map) file.

    Realm-agnostic: the weight file encodes the SE-grid -> lat/lon mapping
    (e.g. map_ne30pg3_to_0.5x0.5_...nc).
    """
    weights = xr.open_dataset(weight_file)
    in_shape = weights.src_grid_dims.load().data

    # xESMF expects 2D vars, so insert a dummy size-1 dimension
    if len(in_shape) == 1:
        in_shape = [1, in_shape.item()]

    out_shape = weights.dst_grid_dims.load().data.tolist()[::-1]

    # bounds (needed for conservative regridding, not for bilinear)
    lat_b_out = np.zeros(out_shape[0] + 1)
    lon_b_out = weights.xv_b.data[: out_shape[1] + 1, 0]
    lat_b_out[:-1] = weights.yv_b.data[np.arange(out_shape[0]) * out_shape[1], 0]
    lat_b_out[-1] = weights.yv_b.data[-1, -1]

    dummy_in = xr.Dataset(
        {
            "lat": ("lat", np.empty((in_shape[0],))),
            "lon": ("lon", np.empty((in_shape[1],))),
            "lat_b": ("lat_b", np.empty((in_shape[0] + 1,))),
            "lon_b": ("lon_b", np.empty((in_shape[1] + 1,))),
        }
    )
    dummy_out = xr.Dataset(
        {
            "lat": ("lat", weights.yc_b.data.reshape(out_shape)[:, 0]),
            "lon": ("lon", weights.xc_b.data.reshape(out_shape)[0, :]),
            "lat_b": ("lat_b", lat_b_out),
            "lon_b": ("lon_b", lon_b_out),
        }
    )

    regridder = xesmf.Regridder(
        dummy_in,
        dummy_out,
        weights=weight_file,
        method=regrid_method,
        reuse_weights=True,
        periodic=True,
    )
    return regridder


def regrid_cam_se_data(regridder, ds_in, debug=False):
    """Regrid all `ncol`-carrying variables of a CAM dataset to lat/lon."""
    if regridder is None:
        print("No data to regrid, returning")
        return ds_in

    dimname = "ncol"
    ds_in_copy = ds_in.copy()

    # variables that carry the SE horizontal dim
    vars_to_regrid = [name for name in ds_in.data_vars if dimname in ds_in[name].dims]

    # keep_attrs so units etc. survive the reshape + regrid
    with xr.set_options(keep_attrs=True):
        for var in vars_to_regrid:
            if debug:
                print(f"var is {var}")
            ds_in_copy[var] = (
                ds_in_copy[var].transpose(..., dimname).expand_dims("dummy", axis=-2)
            )

        ds_out = regridder(ds_in_copy.rename({"dummy": "lat", dimname: "lon"}))

    # restore pass-through vars (hyam/hybm/..., time_bnds, gw, ...) + attrs
    ds_out = _restore_passthrough_and_attrs(ds_out, ds_in, horiz_dim=dimname)
    return ds_out
