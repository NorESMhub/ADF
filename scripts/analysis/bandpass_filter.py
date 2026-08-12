"""
Applying a bandpass filter
(the difference of two lowpass lanczos filters)
to a time-series.
==================================

This example demonstrates low pass filtering a time-series by applying a
weighted running mean over the time dimension.

The time-series used here is the EAR5 Reanalysis hourly 850hpa vorticity,
which is first averaged to daily data, and then filtered using two different
Lanczos filters, one to filter out time-scales of less than 3 years and one
to filter out time-scales of less than 10 years.

References
----------

    Duchon C. E. (1979) Lanczos Filtering in One and Two Dimensions.
    Journal of Applied Meteorology, Vol 18, pp 1016-1022.

"""

import numpy as np
import xarray as xr
import glob
import os
from pathlib import Path

def low_pass_weights(window, cutoff):
    """Calculate weights for a low pass Lanczos filter.

    Args:

    window: int
        The length of the filter window.

    cutoff: float
        The cutoff frequency in inverse time steps.

    """
    order = ((window - 1) // 2 ) + 1
    nwts = 2 * order + 1
    w = np.zeros([nwts])
    n = nwts // 2
    w[n] = 2 * cutoff
    k = np.arange(1., n)
    sigma = np.sin(np.pi * k / n) * n / (np.pi * k)
    firstfactor = np.sin(2. * np.pi * cutoff * k) / (np.pi * k)
    w[n-1:0:-1] = firstfactor * sigma
    w[n+1:-1] = firstfactor * sigma
    return w[1:-1]


def _single_stream(value):
    """Reduce a (possibly nested) hist_str value to a single stream string.

    ADF specially processes any config key whose name contains 'hist_str'
    (see adf_info.hist_str_to_list): it wraps the value into a (possibly nested)
    list to support multiple streams per case. The bandpass diagnostic uses a
    single stream, so collapse the value down to the first string.
    """
    while isinstance(value, (list, tuple)) and value:
        value = value[0]
    return value


def bandpass_filter(
    adf,
    ):
    
    # window length for filters
    window = 50

    # construct 3 days and 10 days low pass filters
    hfw = low_pass_weights(window, 1. / 2.5)
    lfw = low_pass_weights(window, 1. / 6.)
    weight_high = xr.DataArray(hfw, dims = ['window'])
    weight_low = xr.DataArray(lfw, dims = ['window'])

    # Raw-model field to bandpass-filter, taken from the config (defaults to 'Z500').
    # The output storm-track variable name and the output file name are
    # both DERIVED from this, so no field name is hard-wired downstream.
    varname = adf.get_basic_info("bandpass_var")
    if not varname:
        varname = "Z500"
    out_varname = f"BP_{varname}"   # e.g. Z500 -> BP_Z500
    print(f"Calculating {out_varname} climo ...")
    
    #CAM simulation variables (these quantities are always lists):
    case_names    = adf.get_cam_info("cam_case_name", required=True)
    input_ts_locs = adf.get_cam_info("cam_ts_loc", required=True)
    datapath = adf.get_cam_info("cam_hist_loc", required=True)

    # History stream (e.g. 'cam.h1a') that holds the sub-monthly Z500 field the
    # bandpass filter needs.  Read from the config instead of hard-wiring the
    # stream per case/model, mirroring how the TEM analysis uses 'tem_hist_str'.
    # One entry per test case; the baseline entry is appended below when used.
    _bp_hist = adf.get_cam_info("bandpass_hist_str", required=True)
    bandpass_hist_strs = list(_bp_hist) if isinstance(_bp_hist, list) else [_bp_hist]

    #Grab case years
    syear_cases = adf.climo_yrs["syears"]
    eyear_cases = adf.climo_yrs["eyears"]
    
    outpath = adf.get_cam_info("cam_climo_loc", required=True) 
    overwrite_file = adf.get_cam_info("cam_overwrite_climo")
    
    #Check if a baseline simulation is also being used:
    if not adf.get_basic_info("compare_obs"):
        #Extract CAM baseline variaables:
        baseline_name     = adf.get_baseline_info("cam_case_name", required=True)
        input_ts_baseline = adf.get_baseline_info("cam_ts_loc", required=True)
        datapath_baseline = adf.get_baseline_info("cam_hist_loc", required=True)
        datapath.append(datapath_baseline)
        
        case_names.append(baseline_name)
        input_ts_locs.append(input_ts_baseline)
        bandpass_hist_strs.append(adf.get_baseline_info("bandpass_hist_str", required=True))

        #Grab baseline years (which may be empty strings if using Obs):
        syear_baseline = adf.climo_yrs["syear_baseline"]
        eyear_baseline = adf.climo_yrs["eyear_baseline"]

        syear_cases.append(syear_baseline)
        eyear_cases.append(eyear_baseline)

        outpath_baseline = adf.get_baseline_info("cam_climo_loc", required=True) 
        outpath.append(outpath_baseline)
        
        overwrite_file.append(adf.get_baseline_info("cam_overwrite_climo"))
    # ADF wraps '*hist_str' values into a (possibly nested) list because the key
    # name contains 'hist_str'; flatten each case entry back to a single stream
    # string so the file glob below is built correctly.
    bandpass_hist_strs = [_single_stream(s) for s in bandpass_hist_strs]
    print("bandpass history streams (per case): ", bandpass_hist_strs)

    # If the model runs on a native spectral-element (ncol) grid, the storm-track
    # climatology comes out on that grid and must be regridded to lat/lon before
    # it is written/plotted.  Gate on 'cam_se_grid' exactly like create_time_series:
    #  - unset  -> input is already lat/lon; do nothing.
    #  - set    -> look up the weight file and build the regridder lazily (once,
    #              on the first SE case) and reuse it for all cases.
    se_grid = adf.get_basic_info("cam_se_grid")
    se_regridder = None
    if se_grid:
        se_weight_file = adf.get_basic_info(
            f"cam_se_weight_file_{se_grid}", required=True
        )
        from adf_se_regrid import make_se_regridder, regrid_cam_se_data

    #Calculate BP Z500 for each case
    count = 0
    for case in case_names:

        c1 = case
        syr = syear_cases[count]
        eyr = eyear_cases[count]

        # History stream that holds the sub-monthly Z500 for this case, taken
        # from the config ('bandpass_hist_str', e.g. 'cam.h1a').  This replaces
        # the previous hard-wired per-case/per-model stream selection.
        hist_str = bandpass_hist_strs[count]
        fname = f'{datapath[count]}/{c1}.{hist_str}.*.nc'
        all_files = glob.glob(fname)

        #Reading amount of files to load from the simulation
        if len(all_files) == 1:
            print("Only one file available")
            filtered_files = all_files
        else:
            filtered_files = [
                f for f in all_files
                if syr-1 <= int(f.split('.')[-2].split('-')[0]) <= eyr+1  # Extract year from filename
            ]
            
        # Create full path name:
        ts_outfil_str = (
            outpath[count]
            + os.sep
            + f"{c1}_{out_varname}_climo.nc"
        )

        # Check if clobber is true for file
        if Path(ts_outfil_str).is_file():
            if overwrite_file[count]:
                Path(ts_outfil_str).unlink()
            else:
                msg = f"\t    INFO: {out_varname} climo file was found "
                msg += "and overwrite is False. Will use existing file."
                print(msg)
                count+=1
                continue
            
        print("years: ", syr, eyr)    
        
        # if the reading crashes due to memory issues you may add chunks, i.e. parallel=True, chunks={"time":12}
        ds = xr.open_mfdataset(
            filtered_files,
            combine="by_coords",
            data_vars=[varname],
            preprocess=None,
            parallel=False,
        )
        '''
        Data from month before and after the specific month are also needed 
        because the time filter requires extra data at the beginning and end.
        
        This means that that it will look for data also in the year before (for January)
        and year after (for December) the selected time-period.
        '''
        # First and last years actually present in this case's data.  The filter
        # needs padding into the neighbouring month, so:
        #   - December of `year` needs data from year+1 (its January pad), and
        #   - January of `year`  needs data from year-1 (its December pad).
        # A month whose pad falls outside the available data is skipped, so the
        # edge months of the run don't produce edge-contaminated values.
        # Deriving these bounds from the data replaces a previously hard-wired year.
        first_data_year = int(ds['time'].dt.year.min())
        last_data_year  = int(ds['time'].dt.year.max())

        da = None
        for mon in range(12):
            clim_dvar = None
            # Include end_year: range() is exclusive of its stop value, so use
            # eyr+1 to average over the full start_year..end_year window given in
            # the config (consistent with the rest of ADF). Edge months whose
            # filter pad is unavailable are still skipped by the guards below.
            for year in range(syr, eyr + 1):
                if mon == 11: #december
                    if year + 1 > last_data_year:  # no next-year data for the pad
                        continue
                    daily_data = ds.sel(time=slice(f"{year:04d}-11-20T00:00:00",f"{year+1:04d}-01-10T23:00:00"))[varname]
                elif mon == 0: #january
                    if year - 1 < first_data_year:  # no previous-year data for the pad
                        continue
                    daily_data = ds.sel(time=slice(f"{year-1:04d}-12-20T00:00:00",f"{year:04d}-02-10T23:00:00"))[varname]
                else: #the other months
                    daily_data = ds.sel(time=slice(f"{year:04d}-{mon:02d}-20T00:00:00",f"{year:04d}-{mon+2:02d}-10T23:00:00"))[varname] 
                
                # apply the filters using the rolling method with the weights
                lowpass_hf = daily_data.rolling(time = len(hfw), center = True).construct('window').dot(weight_high)
                lowpass_lf = daily_data.rolling(time = len(lfw), center = True).construct('window').dot(weight_low)

                # the bandpass is the difference of two lowpass filters.
                bandpass = lowpass_hf - lowpass_lf

                # select the data for the specific month
                bandpass = bandpass.sel(time=bandpass.time.dt.month.isin([mon+1]))
                
                # get the standard deviation to find the BP Z500
                dvar = xr.DataArray.std(bandpass, dim = 'time', skipna = True)
                
                # combine into one Dataset with all years
                dvar = dvar.assign_coords(year=year)
                if isinstance(clim_dvar, xr.Dataset):
                    clim_dvar = xr.concat([clim_dvar,dvar.to_dataset(name=out_varname)],dim="year")    
                else:
                    clim_dvar = dvar.to_dataset(name=out_varname)
            
            # No valid years for this month (e.g. a short/single-year run where
            # the only year's edge-month pad is unavailable, so every year was
            # skipped above). Skip the month rather than crash on
            # None.expand_dims; it is simply absent from the climatology.
            if clim_dvar is None:
                print(f"\t    WARNING: no valid years for month {mon+1} of "
                      f"'{c1}'; it will be absent from {out_varname}.")
                continue

            # combining the different months in the same Dataset
            if isinstance(da,xr.Dataset):
                clim_dvar = clim_dvar.expand_dims(time=[mon])
                da = xr.concat([da,clim_dvar],dim="time")
            else:
                clim_dvar = clim_dvar.expand_dims(time=[mon])
                da = clim_dvar
        
        # Calculating the climatology
        da = da.mean(dim="year")
        print(da)

        # Close datasets
        ds.close()
        clim_dvar.close()
        dvar.close()

        # Regrid the (small) 12-month climatology from native SE (ncol) to lat/lon
        # if the model is on an SE grid.  The per-case 'ncol' check keeps lat/lon
        # cases (e.g. an obs/lat-lon baseline) untouched even when se_grid is set.
        if se_grid and "ncol" in da.dims:
            if se_regridder is None:
                se_regridder = make_se_regridder(weight_file=se_weight_file)
            da = regrid_cam_se_data(se_regridder, da)

        # save the dataset in the same folder as the other climo datasets
        da.to_netcdf(ts_outfil_str)
        
        count += 1
    
    print("done")
    return

