# ADF diagnostics

[![Framework Unit Tests](https://github.com/NCAR/ADF/actions/workflows/ADF_unit_tests.yaml/badge.svg)](https://github.com/NCAR/ADF/actions/workflows/ADF_unit_tests.yaml) [![pre-commit](https://github.com/NCAR/ADF/actions/workflows/ADF_pre-commit.yaml/badge.svg)](https://github.com/NCAR/ADF/actions/workflows/ADF_pre-commit.yaml) [![CC BY 4.0][cc-by-shield]][cc-by]

This repository contains the Atmosphere Model Working Group (AMWG) Diagnostics Framework (ADF) diagnostics python package, which includes numerous different averaging,
re-gridding, and plotting scripts, most of which are provided by users of CAM itself.

Specifically, this package is currently designed to generate standard climatological comparisons between either two
different CAM simulations, or between a CAM simulation and observational and reanalysis datasets.  Ideally
this will allow for a quick evaluation of a CAM simulation, without requiring the user to generate numerous
different figures on their own.

Currently, this package only uses standard CAM monthly time-slice (h0) outputs or single-variable monthly time series files.  However, if there is user interest then
additional model input options can be added.

Finally, if you are interested in general (but non-supported) tools used by AMP scientists and engineers in their work, then please check out the [AMP Toolbox](https://github.com/NCAR/AMP_toolbox).

## Required software environment

### Python environment
These diagnostics currently require Python version 3.6 or higher.  They also require the following non-standard python libraries/modules:

- PyYAML
- Numpy
- Xarray
- Matplotlib
- Cartopy
- GeoCAT
- xESMF (needed if SE->lat/lon mapping will occur)

If one wants to generate the "AMWG" model variable statistics table as well, then these additional python libraries are also needed:

- Scipy
- Pandas

On NCAR's CISL machines (cheyenne and casper), these can be loaded by running the following on the command line:
```
module load conda
conda activate npl
```

On NIRD IPCC machine
```
conda activate /projects/NS9560K/diagnostics/ADF/envs/adf_v0.14
```

On a non-CISL or non-NIRD machine, you can create and activate the appropriate python enviroment using the `env/conda_environment.yaml` file like so:
```
conda env create -f env/conda_environment.yaml
conda activate adf_v1.0.0
```

###  NetCDF Operator (NCO) suite
The `ncrcat` NetCDF Operator (NCO) is also needed.
- On the CISL machines this can be loaded by simply running:
```
module load nco
``` 
- On the CGD machines by simply running:
```
module load tool/nco
```
- On the NIRD machine run:
```
module load NCO/5.0.3-intel-2021b
```

### Climate Variability Diagnostics

Finally, if you also want to run the [Climate Variability Diagnostics Package](https://www.cesm.ucar.edu/working_groups/CVC/cvdp/) (CVDP) as part of the ADF then you'll also need NCL.
On the CISL machines this can be done using the command:
```
module load ncl
```
or on the CGD machines by using the command:
```
module load tool/ncl/6.6.2
```
on the command line.

## Running ADF diagnostics

A detailed summary of the input yaml file is provided in [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md).

Detailed instructions for users and developers are availabe on this repository's [wiki](https://github.com/NCAR/ADF/wiki).

To run an example of the ADF diagnostics, simply download this repo, setup your computing environment as described in the [Required software environment](https://github.com/NCAR/CAM_diagnostics/blob/main/README.md#required-software-environment) section above, modify the `config_cam_baseline_example.yaml` file (or create one of your own) to point to the relevant diretories and run:

`./run_adf_diag config_cam_baseline_example.yaml`

This should generate a collection of time series files, climatology (climo) files, re-gridded climo files, and example ADF diagnostic figures, all in their respective directories.

### ADF Tutorial/Demo

Jupyter Book detailing the ADF including ADF basics, guided examples, quick runs, and references
  - https://justin-richling.github.io/ADF-Tutorial/README.html

## Troubleshooting

Any problems or issues with this software should be posted on the ADF discussions page located online [here](https://github.com/NCAR/ADF/discussions).

Please note that registration may be required before a message can
be posted.  However, feel free to search the forums for similar issues
(and possible solutions) without needing to register or sign in.

Good luck, and have a great day!

##

This work is licensed under a
[Creative Commons Attribution 4.0 International License][cc-by].

[![CC BY 4.0][cc-by-image]][cc-by]

[cc-by]: http://creativecommons.org/licenses/by/4.0/
[cc-by-image]: https://i.creativecommons.org/l/by/4.0/88x31.png
[cc-by-shield]: https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg
