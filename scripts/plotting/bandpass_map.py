"""
bandpass_map
============

Plot the bandpass-filtered storm-track climatology (``BP_<var>``) produced by
the ``bandpass_filter`` analysis script.

The analysis step writes one climatology file per case into ``cam_climo_loc``:

    <case>_BP_<var>_climo.nc          (12 monthly maps of storm-track amplitude)

This script reads those files and, for each test case, draws seasonal
(ANN, DJF, MAM, JJA, SON) maps:

  * model-vs-baseline  -> a 3-panel test / baseline / difference map
                          (the baseline is regridded onto the test grid first,
                          since the two BP files may be on different grids).
  * compare_obs        -> ADF has no observed storm-track climatology, so only
                          the test case is drawn (single map) and a warning is
                          issued.

The field name is derived from the ``bandpass_var`` config option (default
``Z500``), exactly as in the analysis script, so the two always agree.
"""

from pathlib import Path
import warnings

import numpy as np
import xarray as xr

import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from cartopy.util import add_cyclic_point

import adf_utils as utils
import plotting_functions as pf


# Seasons to plot (matches the other ADF map scripts).
_SEASONS = ["ANN", "DJF", "MAM", "JJA", "SON"]

# Website grouping for these plots.
_WEB_CATEGORY = "Storm Tracks"


def _load_bp_climo(path, bp_var):
    """Open a BP climatology file and return the ``bp_var`` DataArray, or None."""
    try:
        ds = xr.open_dataset(path)
    except (FileNotFoundError, OSError, ValueError) as err:
        warnings.warn(f"bandpass_map: could not open {path}: {err}")
        return None
    if bp_var not in ds:
        warnings.warn(f"bandpass_map: '{bp_var}' not found in {path}; skipping.")
        ds.close()
        return None
    return ds[bp_var]


def _match_grid(ref2d, tgt2d):
    """Regrid a 2-D reference field onto the target's lat/lon grid if they differ.

    The test and baseline BP files can be on different grids (each case is
    regridded to its own SE target in the analysis step), so bilinear-interpolate
    the reference onto the test grid before differencing.  A no-op when the grids
    already match.
    """
    if not all(d in ref2d.dims for d in ("lat", "lon")):
        return ref2d
    if not all(d in tgt2d.dims for d in ("lat", "lon")):
        return ref2d
    same = (ref2d.sizes["lat"] == tgt2d.sizes["lat"]
            and ref2d.sizes["lon"] == tgt2d.sizes["lon"])
    if same:
        return ref2d
    return ref2d.interp_like(tgt2d)


def _plot_single_map(wks, case_label, climo_yrs, field, bp_var, season, vres):
    """Draw a single-panel lat/lon map (used when there is no reference)."""
    cmap = vres.get("colormap", "plasma")
    levels = vres.get("contour_levels")

    # Add a cyclic point in longitude so the map has no seam at 0/360.
    try:
        arr, lon_c = add_cyclic_point(field.values, coord=field["lon"].values)
    except (ValueError, KeyError):
        arr, lon_c = field.values, field["lon"].values

    contourf_kw = {"cmap": cmap, "extend": "both", "transform": ccrs.PlateCarree()}
    if levels is not None:
        contourf_kw["levels"] = levels

    fig = plt.figure(figsize=(8, 4.5))
    ax = plt.axes(projection=ccrs.PlateCarree())
    filled = ax.contourf(lon_c, field["lat"].values, arr, **contourf_kw)
    ax.coastlines()
    ax.set_global()
    cbar = fig.colorbar(filled, ax=ax, orientation="vertical", shrink=0.7, pad=0.02)
    cbar.set_label(field.attrs.get("units", ""))
    yr_txt = f"{climo_yrs[0]}-{climo_yrs[1]}" if climo_yrs and climo_yrs[0] != "" else ""
    ax.set_title(f"{case_label}   {bp_var}   {season}   {yr_txt}".strip())
    fig.savefig(wks, bbox_inches="tight", dpi=150)
    plt.close(fig)


def bandpass_map(adfobj):
    """Generate storm-track (bandpass) climatology maps."""

    # --- field name (must match the bandpass_filter analysis script) ---
    varname = adfobj.get_basic_info("bandpass_var")
    if not varname:
        varname = "Z500"
    bp_var = f"BP_{varname}"

    # --- plot options ---
    plot_type = adfobj.read_config_var("diag_basic_info").get("plot_type", "png")
    redo_plot = adfobj.get_basic_info("redo_plot")

    # Variable-specific plot options (colormap, contour levels, ...) if present.
    vres = adfobj.variable_defaults.get(bp_var, {})
    web_category = vres.get("category", _WEB_CATEGORY)
    # Only the plot-styling keys go to plot_map_and_save; obs_*/category are not
    # matplotlib options and are consumed elsewhere in this script.
    _PLOT_KEYS = {"colormap", "contour_levels", "diff_colormap",
                  "diff_contour_levels", "tiString", "tiFontSize", "mpl"}
    plot_kwargs = {k: v for k, v in vres.items() if k in _PLOT_KEYS}

    # --- test cases (index-aligned with plot_location / nicknames) ---
    test_cases = adfobj.data.case_names
    test_climo_locs = adfobj.get_cam_info("cam_climo_loc", required=True)
    test_nicknames = adfobj.data.test_nicknames

    # --- case / baseline year annotations ---
    syears = adfobj.climo_yrs["syears"]
    eyears = adfobj.climo_yrs["eyears"]
    syear_base = adfobj.climo_yrs["syear_baseline"]
    eyear_base = adfobj.climo_yrs["eyear_baseline"]

    # --- reference climatology ---
    # compare_obs : the reference is the observed (e.g. ERA5) storm-track
    #     climatology named in the BP_<var> variable defaults (obs_file /
    #     obs_var_name), resolved under 'obs_data_loc' like ADF's obs machinery.
    # otherwise   : the reference is the CAM baseline's own BP_<var> climo file.
    # If the reference can't be found we fall back to test-only maps + a warning.
    compare_obs = adfobj.compare_obs
    ref_da = None
    if compare_obs:
        base_nickname = vres.get("obs_name", "obs")
        obs_file = vres.get("obs_file")
        obs_var_name = vres.get("obs_var_name", varname)
        if not obs_file:
            warnings.warn(f"bandpass_map: compare_obs is set but '{bp_var}' has no "
                          "'obs_file' in the variable defaults; plotting test case(s) only.")
        else:
            # Resolve as an absolute path, else relative to obs_data_loc.
            obs_data_loc = adfobj.get_basic_info("obs_data_loc")
            obs_path = Path(obs_file)
            if not obs_path.is_file() and obs_data_loc:
                obs_path = Path(obs_data_loc) / obs_file
            if obs_path.is_file():
                ref_da = _load_bp_climo(obs_path, obs_var_name)
            else:
                warnings.warn(f"bandpass_map: obs file not found ({obs_path}); "
                              "plotting test case(s) only.")
    else:
        base_nickname = adfobj.data.ref_nickname
        base_name = adfobj.get_baseline_info("cam_case_name", required=True)
        base_climo_loc = adfobj.get_baseline_info("cam_climo_loc", required=True)
        ref_file = Path(base_climo_loc) / f"{base_name}_{bp_var}_climo.nc"
        if ref_file.is_file():
            ref_da = _load_bp_climo(ref_file, bp_var)
        else:
            warnings.warn(f"bandpass_map: reference file not found ({ref_file}); "
                          "plotting the test case(s) only.")

    # --- loop over test cases ---
    for case_idx, case_name in enumerate(test_cases):
        plot_loc = Path(adfobj.plot_location[case_idx])
        plot_loc.mkdir(parents=True, exist_ok=True)

        test_file = Path(test_climo_locs[case_idx]) / f"{case_name}_{bp_var}_climo.nc"
        if not test_file.is_file():
            warnings.warn(f"bandpass_map: test file not found ({test_file}); skipping case.")
            continue
        test_da = _load_bp_climo(test_file, bp_var)
        if test_da is None:
            continue

        # seasonal_mean assumes a 12-month climatology; guard the degenerate case.
        if test_da.sizes.get("time", 0) != 12:
            warnings.warn(f"bandpass_map: {test_file.name} does not have 12 months "
                          f"(got {test_da.sizes.get('time', 0)}); skipping case.")
            continue

        case_nick = test_nicknames[case_idx] if case_idx < len(test_nicknames) else case_name
        case_yrs = [syears[case_idx], eyears[case_idx]]
        base_yrs = [syear_base, eyear_base]

        have_ref = ref_da is not None

        for season in _SEASONS:
            # Three views of this season's storm-track climatology.  The two
            # stereographic polar views (make_polar_plot) need both a test and a
            # reference field, so they are only produced when a reference is
            # available; the test-only fallback keeps just the single LatLon map.
            latlon_wks = plot_loc / f"{bp_var}_{season}_LatLon_Mean.{plot_type}"
            wanted = [(latlon_wks, "LatLon")]
            if have_ref:
                wanted.append((plot_loc / f"{bp_var}_{season}_NHPolar_Mean.{plot_type}", "NHPolar"))
                wanted.append((plot_loc / f"{bp_var}_{season}_SHPolar_Mean.{plot_type}", "SHPolar"))

            # redo_plot handling: reuse an existing plot unless redo is requested.
            # Register+skip the ones already on disk; collect the rest to draw.
            todo = []
            for wks, ptype in wanted:
                if wks.is_file():
                    if redo_plot:
                        wks.unlink()
                    else:
                        adfobj.add_website_data(wks, bp_var, case_name, category=web_category,
                                                season=season, plot_type=ptype)
                        continue
                todo.append((wks, ptype))
            if not todo:
                continue

            # Seasonal mean(s) -- computed once and reused across the LatLon /
            # NHPolar / SHPolar views of this season.
            mseason = utils.seasonal_mean(test_da, season=season, is_climo=True)
            if have_ref:
                # make_polar_plot slices lat as slice(45,90)/slice(-90,-45),
                # which assumes ascending latitude; sort both fields so the polar
                # views work regardless of the climo file's lat ordering.
                mseason = mseason.sortby("lat")
                oseason = utils.seasonal_mean(ref_da, season=season, is_climo=True).sortby("lat")
                oseason = _match_grid(oseason, mseason)
                dseason = mseason - oseason
                pseason = (mseason - oseason) / np.abs(oseason) * 100.0
                pseason = pseason.where(np.isfinite(pseason), np.nan)
                # make_polar_plot labels the colorbar with d1.units; xarray
                # arithmetic dropped attrs, so ensure a 'units' attribute exists
                # (BP_<var> is a std of Z500 -> metres) to avoid an AttributeError.
                _bp_units = vres.get("units", getattr(test_da, "units", "m"))
                mseason.attrs.setdefault("units", _bp_units)
                oseason.attrs.setdefault("units", _bp_units)

            for wks, ptype in todo:
                if ptype == "LatLon":
                    if have_ref:
                        pf.plot_map_and_save(
                            wks, case_nick, base_nickname,
                            case_yrs, base_yrs,
                            mseason, oseason, dseason, pseason,
                            obs=compare_obs, **plot_kwargs,
                        )
                    else:
                        _plot_single_map(wks, case_nick, case_yrs, mseason, bp_var, season, vres)
                else:
                    # ptype is "NHPolar" or "SHPolar"
                    pf.make_polar_plot(
                        wks, case_nick, base_nickname,
                        case_yrs, base_yrs,
                        mseason, oseason, dseason, pseason,
                        hemisphere=("NH" if ptype == "NHPolar" else "SH"),
                        obs=compare_obs, **plot_kwargs,
                    )

                adfobj.add_website_data(wks, bp_var, case_name, category=web_category,
                                        season=season, plot_type=ptype)

    print("  ...storm-track (bandpass) maps have been generated successfully.")
