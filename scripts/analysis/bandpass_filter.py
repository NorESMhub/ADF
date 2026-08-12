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

# import pandas as pd
# import matplotlib.pyplot as plt
# from matplotlib.pyplot import plot, savefig
# import matplotlib.colors
# import cartopy.crs as ccrs
# import matplotlib.ticker as mticker
# from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER



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


#Import ADF diagnostics object:
# from adf_diag import AdfDiag


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


    varname = "Z500" #variable name in the raw modelfiles


    print("Calculating BP Z500 climo ...")
    
    #CAM simulation variables (these quantities are always lists):
    case_names    = adf.get_cam_info("cam_case_name", required=True)
    input_ts_locs = adf.get_cam_info("cam_ts_loc", required=True)
    datapath = adf.get_cam_info("cam_hist_loc", required=True)


#    config_yaml = "/nird/datalake/NS9560K/andrear/diagnostics/config_noresm_template_base.yaml"
#    #Initalize CAM diagnostics object:
#    diag = AdfDiag(config_yaml, debug=config_debug)

#    #Create model time series.
#    print(diag.diag_var_list)

#    diag.diag_var_list = ["BP_Z500"]
#    #Please note that this is an internal ADF function:
#    diag.create_time_series()

#    # adf.diag_var_list = ["BP_Z500"]


    
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

        #Grab baseline years (which may be empty strings if using Obs):
        syear_baseline = adf.climo_yrs["syear_baseline"]
        eyear_baseline = adf.climo_yrs["eyear_baseline"]

        syear_cases.append(syear_baseline)
        eyear_cases.append(eyear_baseline)

        outpath_baseline = adf.get_baseline_info("cam_climo_loc", required=True) 
        outpath.append(outpath_baseline)
        
        overwrite_file.append(adf.get_baseline_info("cam_overwrite_climo"))


    print("test hist string case: ", adf.hist_string["test_hist_str"])
    count = 0
    #Calculate BP Z500 for each case
    for case in case_names:

        c1 = case
        syr = syear_cases[count]
        eyr = eyear_cases[count]

        #Check if specific CESM3 case, contains daily output in h2 instead of h1
        print(datapath[count])
        if c1 == "b.e30_alpha08b.B1850C_LTso.ne30_t232_wgx3.316":
            fname = f'{datapath[count]}/{c1}.cam.h2a.*.nc'
        elif adf.hist_string["test_hist_str"] == "cam.h0":
            #datapath[count] == f"/nird/datapeak/NS9560K/noresm/cases/{case}/atm/hist": #The path to NorESM2 cases, which only uses h1 (not h1a) /nird/datapeak/NS9560K/noresm/cases/N1850_f19_tn14_20190621/atm/hist
            fname = f'{datapath[count]}/{c1}.cam.h1.*.nc'
            print("test success")
        else:
            fname = f'{datapath[count]}/{c1}.cam.h1a.*.nc'
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
            + "_".join([c1, "BP_Z500_climo.nc"])
        )

        # Check if clobber is true for file
        if Path(ts_outfil_str).is_file():
            if overwrite_file[count]:
                Path(ts_outfil_str).unlink()
            else:
                msg = f"\t    INFO: BP_Z500 climo file was found "
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
        da = None
        for mon in range(12):
            clim_dvar = None
            for year in range(syr,eyr):
                if mon == 11: #december
                    if year == 2014: continue
                    daily_data = ds.sel(time=slice(f"{year:04d}-11-20T00:00:00",f"{year+1:04d}-01-10T23:00:00"))[varname] 
                elif mon == 0: #january
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
                    clim_dvar = xr.concat([clim_dvar,dvar.to_dataset(name="BP_Z500")],dim="year")    
                else:
                    clim_dvar = dvar.to_dataset(name="BP_Z500")
            
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

        ds.close()
        clim_dvar.close()
        dvar.close()

        # save the dataset in the same folder as the other climo datasets
        da.to_netcdf(f"{outpath[count]}/{c1}_BP_Z500_climo.nc")
        
        count += 1
    
    print("done")
    return

