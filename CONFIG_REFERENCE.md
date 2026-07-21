# ADF config reference

A scannable reference for the ADF YAML config
(see `config_noresm_default.yaml` as an example).

- **Run/edit** one of the the bare-bones file (e.g. `config_noresm_default.yaml`) — no comments, just values.
- **Look things up** here.

> Every key below lives under a top-level *section* (e.g. `diag_basic_info:`).
> Indentation and section placement matter — a key placed in the wrong section
> is silently ignored.

---

## Contents

- [What a complete config file must contain](#what-a-complete-config-file-must-contain)
  - [Tier 1 — Required (ADF fails or produces nothing without them)](#tier-1--truly-required-adf-fails-or-produces-nothing-without-them)
  - [Tier 2 — Optional features (off unless you turn them on)](#tier-2--optional-features-off-unless-you-turn-them-on)
- [Variable substitution (`${...}`)](#variable-substitution-)
- [Top-level keys](#top-level-keys)
- [`Section: diag_basic_info`](#section-diag_basic_info)
  - [SE (`ncol`) → lat/lon regridding — how it works](#se-ncol--latlon-regridding--how-it-works)
- [`Section: diag_cam_climo`](#section-diag_cam_climo)
- [`Section: diag_cam_baseline_climo`](#section-diag_cam_baseline_climo)
- [`Section: diag_cvdp_info`](#section-diag_cvdp_info)
- [`Section: diag_mdtf_info`](#section-diag_mdtf_info)
- [`Section: time_averaging_scripts`](#section-time_averaging_scripts)
- [`Section: regridding_scripts`](#section-regridding_scripts)
- [`Section: analysis_scripts`](#section-analysis_scripts)
- [`Section: plotting_scripts`](#section-plotting_scripts)
- [`Section: diag_var_list`](#section-diag_var_list)
- [`Section: region_multicase`](#section-region_multicase)

---

## What a complete config file must contain

Sections fall into **two tiers**:, not simply "required vs optional":

### Tier 1 — Truly required (ADF fails or produces nothing without them)

| Section | Notes |
|---------|-------|
| `diag_basic_info` | Basic info that applies to all runs. |
| `diag_cam_climo` | The case being diagnosed. |
| `diag_var_list` | Which variables to process/plot. |
| `diag_cam_baseline_climo` | **Required when `compare_obs: false`** (model-vs-model) — the baseline case to compare against. Not needed when `compare_obs: true`. |
| `time_averaging_scripts` | Climatology creation |
| `regridding_scripts` | Regrid model lat/lon climo → observation/baseline grid (+ vertical interp, hybrid→pressure) so model and reference are directly comparable |
| `analysis_scripts` | Tables (e.g. `amwg_table`) |
| `plotting_scripts` | Plots |

> **Note — there are two different "regriddings" that occur :** `regridding_scripts`
> (`regrid_and_vert_interp`) regrids the model's **lat/lon** climatology onto the
> **observation/baseline** grid for comparison. This is *separate* from the
> SE regridding, which converts native **`ncol` → lat/lon** during
> time-series creation (see the "SE (`ncol`) → lat/lon regridding" section).

### Tier 2 — Optional features (off unless you turn them on)

| Section | Notes |
|---------|-------|
| `diag_cvdp_info` | **Omit the whole section to disable**, or keep it with `cvdp_run: false`. Equivalent — a missing section is read as `None` and skipped. |
| `diag_mdtf_info` | **Omit the whole section to disable**, or keep it with `mdtf_run: false`. Same behavior as CVDP. |
| `region_multicase` | **Omit to disable.** Only used when `regional_map_multicase` is in `plotting_scripts`. Missing section → read as `None` → skipped. |

---

## Variable substitution (`${...}`)

| Form | Meaning | Example |
|------|---------|---------|
| `${xxx}` | Substitute the value of `xxx` (must exist in exactly one place) | `cam_climo_loc: /some/where/${user}` |
| `${section.xxx}` | Substitute `xxx` from a specific section (needed when the key repeats) | `${diag_cam_climo.cam_case_name}` |

Notes: keywords must be **lowercase**; avoid periods (`.`) in variable names (breaks the parser).

---

## Top-level keys

| Key | Required | Example | Description |
|-----|----------|---------|-------------|
| `user` | **yes** | `<user_name>` | Username; used in many default paths. `USER-NAME-NOT-SET` is the "not customized" sentinel. |
| `case` | **yes** | `<case name>` | The primary case name. The config references it as `${case}` (e.g. `cam_case_name: ${case}`), so it must be set or the substitution fails. |
| `nick` | **yes** | `<case nickname>` | Nickname for the primary case, referenced as `${nick}` (e.g. `case_nickname: ${nick}`). Must be set wherever `${nick}` is used. |
| `case_base` | **yes if `compare_obs: false`** | `<case_base>` | The baseline case name, referenced as `${case2}`. Required for the model-vs-model comparison. |
| `nick_base` | **yes if `compare_obs: false`** | `<case_base nickname>` | Baseline nickname, referenced as `${nick2}`. |

---

## `Section: diag_basic_info`
Settings shared by all runs.

| Key | Required | Default | Description |
|-----|----------|---------|-------------|
| `hist_str` | optional | `cam.h0a` | History file string to match (only affects time series). No trailing `.`. |
| `compare_obs` | optional | `false` | `true` = model-vs-observations; `false`/missing = model-vs-model. |
| `create_html` | optional | `false` | Generate the HTML website (under `cam_diag_plot_loc/<diag_run>/website`). |
| `obs_data_loc` | if `compare_obs` | — | Location of observational datasets. |
| `cam_regrid_loc` | **yes** | — | Where regridded/interpolated **climatology** files are stored. |
| `cam_overwrite_regrid` | optional | `false` | `false`/missing = skip regridding for files that already exist in `cam_regrid_loc`. |
| **`cam_se_grid`** | optional | *(unset)* | **SE→lat/lon regrid ON/OFF switch.** See the SE regridding section below. |
| **`cam_se_weight_file_ne16`** | if `cam_se_grid: ne16` | — | ESMF weight (map) file, ne16pg3 → 1.9×2.5. |
| **`cam_se_weight_file_ne30`** | if `cam_se_grid: ne30` | — | ESMF weight (map) file, ne30pg3 → 0.5×0.5. |
| `cam_diag_plot_loc` | **yes** | — | Where diagnostic plots are written. |
| `defaults_file` | optional | `lib/adf_variable_defaults.yaml` | Custom variable-plotting defaults YAML (**replaces** the base file entirely). |
| `defaults_overlay_file` | **required** | *(none)* | A second variable-defaults YAML **overlaid** on the base — each variable it lists **replaces** that base entry; unlisted variables keep the base. Each model keeps only the variables that differ (e.g. aerosols) here instead of duplicating the whole file. A bare filename resolves against `lib/`. The aerosol variable defaults (including `aerosol_zonal_list` and the derived aerosols' `derivable_from`/`derivation_formula`) live **only** in the overlays, not the base, and aerosols are always part of a CESM/NorESM run — so this **must** be set (`adf_variable_defaults_noresm.yaml` for NorESM, `adf_variable_defaults_cesm.yaml` for CESM), or the aerosol variables won't derive and lose their plotting defaults. |
| `plot_press_levels` | optional | *(none)* | Pressure levels (hPa) for 3-D vars on lat/lon maps, e.g. `[200,500,850]`. If missing, no 3-D vars plotted on horizontal maps. |
| `central_longitude` | optional | `180` | Center longitude for lat/lon maps. |
| `num_procs` | optional | `1` | Processors for parallel steps. `"*"` = all on the node. Does **not** affect SE regrid (that runs serially). |
| `redo_plot` | optional | `false` | `true` = remake plots even if they exist. |

---

### SE (`ncol`) → lat/lon regridding — how it works

The three `cam_se_*` keys control **in-core** regridding of native CAM
spectral-element output to a regular lat/lon grid. It happens automatically
during time-series creation: each time-series file is written on the native
`ncol` grid and then **overwritten in place** with its lat/lon equivalent, so
every downstream step (climatologies, tables, plots) reads lat/lon.

**On/off switch — `cam_se_grid`:**

| Value | Effect |
|-------|--------|
| `ne16` or `ne30` | Regridding **ON**, using the matching `cam_se_weight_file_*`. |
| unset / blank | Regridding **OFF** — ADF behaves exactly like stock. Use for already-lat/lon input. |

**Key facts (things that cost time to learn the hard way):**

- **Placement matters:** `cam_se_grid` **must** be in `diag_basic_info` (it's read via `get_basic_info`). Elsewhere = silently ignored, no regridding.
- **ADF does not inspect the data** to decide whether to regrid — the decision is purely this setting. Safety net: any file with no `ncol` dimension (already lat/lon) is skipped untouched, so leaving the switch on for lat/lon input is harmless.
- **The target resolution is baked into the weight file** (ne16 → 1.9×2.5, ne30 → 0.5×0.5), *not* chosen here. To change the output grid, use a different weight file.
- **The weight file's source grid must match the data** (ne16 file expects ne16pg3, ne30 expects ne30pg3), else xESMF errors on a shape mismatch — which is your safeguard against picking the wrong file.
- **Runs serially, not under `mp.Pool`** — xESMF/ESMF is not fork-safe (a forked worker deadlocks). So `num_procs` does not speed it up, but the regrid is cheap (applying precomputed weights).

---

## `Section: diag_cam_climo`
The case being diagnosed.

| Key | Required | Example / Default | Description |
|-----|----------|-------------------|-------------|
| `hist_str` | optional | `cam.h0a` | History file(s) to match; list allowed, e.g. `[cam.h2,cam.h0]`. |
| `calc_cam_climo` | optional | `true` | `false` = don't create climatology files. |
| `cam_overwrite_climo` | optional | `false` | `false`/missing = skip existing climo files. |
| `cam_case_name` | **yes** | `n1850.ne30_tn14...` | CAM case (run) name. |
| `case_nickname` | optional | *(= `cam_case_name`)* | Display nickname. Quote it if it starts with `0`. |
| `cam_hist_loc` | **yes** | `.../cases/${...}/atm/hist` | Location of CAM history (h0a) files. Point at **native `ncol`** history for in-core regrid, or at pre-regridded lat/lon files to skip it. |
| `cam_climo_loc` | **yes** | `/scratch/${user}/.../climo` | Where climatologies are created/stored. |
| `start_year` | optional | *(earliest)* | First model year for time series. Blank = earliest available. |
| `end_year` | optional | *(latest)* | Last model year for time series. Blank = latest available. |
| `cam_ts_done` | optional | `false` | `true` = model files are already time series (skip creation). |
| `cam_ts_save` | optional | `false` | `true` = keep interim time-series files (uses disk, saves time later). |
| `cam_overwrite_ts` | optional | `false` | `false` = skip time-series creation if files are found. Set `true` to force rebuild. |
| `cam_ts_loc` | **yes** | `/scratch/${user}/.../tseries` | Where time-series files are (or will be) stored. |
| `tem_hist_str` | optional | `cam.h4` | TEM history file string. |
| `cam_tem_loc` | optional | `.../tem/` | Where TEM files are stored. **If unset/commented, TEM is skipped.** |
| `overwrite_tem` | optional | `false` | `false` = skip TEM creation if files found. |

---

## `Section: diag_cam_baseline_climo`
The baseline case (only if `compare_obs: false`).

Same keys as `diag_cam_climo` (reference them as `${diag_cam_baseline_climo.xxx}`).
Distinct values worth noting:

| Key | Example | Description |
|-----|---------|-------------|
| `cam_case_name` | `n1850.ne30_tn14...20241204` | Baseline case name. |
| `cam_hist_loc` | `.../cases/${diag_cam_baseline_climo.cam_case_name}/atm/hist` | Baseline history location. |
| `cam_ts_loc` | `/scratch/${user}/diagnostics/ADF/${...}/atm/tseries` | Baseline time-series location. |
| `start_year` / `end_year` | `52` / `71` | Baseline year range. |

*(All other keys mirror `diag_cam_climo`.)*

---

## `Section: diag_cvdp_info`
Climate Variability Diagnostics Package (optional).

| Key | Default | Description |
|-----|---------|-------------|
| `cvdp_run` | `false` | Run CVDP (in background; finishes after ADF). Needs `PSL, TREFHT, TS, PRECT` (or `PRECC`+`PRECL`) in `diag_var_list`. |
| `cvdp_codebase_loc` | — | Path to the CVDP codebase. |
| `cvdp_loc` | — | Where CVDP is copied to and plots stored. |
| `cvdp_tar` | `false` | Tar up CVDP results. |

---

## `Section: diag_mdtf_info`
NOAA MDTF (Model Diagnostics Task Force) diagnostics (optional, CASPER only).

| Key | Default | Description |
|-----|---------|-------------|
| `mdtf_run` | `false` | Run MDTF (background). |
| `mdtf_input_settings_filename` | `mdtf_input.json` | JSON ADF writes for MDTF input. |
| `mdtf_codebase_path` / `mdtf_codebase_loc` | — | MDTF codebase locations. |
| `conda_root` / `conda_env_root` | — | Conda locations for MDTF envs. |
| `OBS_DATA_ROOT` | — | MDTF observation data root. |
| `MODEL_DATA_ROOT` | `${diag_cam_climo.cam_ts_loc}/mdtf/...` | Writable dir where ADF stages ts files for MDTF. |
| `pod_list` | `["MJO_suite"]` | Which PODs (diagnostics) to run — each needs specific variables. |
| `make_variab_tar`, `save_ps`, `save_nc`, `overwrite`, `verbose`, `test_mode`, `dry_run` | — | Output/debug toggles. |

---

## `Section: time_averaging_scripts`
Climatology averaging. Add any of the scripts in `scripts/averaging/` directory but without the .`py` extension.

| Script | What it does |
|--------|--------------|
| `create_climo_files` | Compute climatologies from the time series. Overwriting is controlled by `cam_overwrite_climo` (not a `clobber` kwarg). |
| `create_TEM_files` | *(optional)* Generate TEM diagnostic input files (for the `tem` plot). |

---

## `Section: regridding_scripts`
Regrid model climo to the reference grid. Add any of the scripts in `scripts/regridding/` directory but without the .`py` extension.

| Script | What it does |
|--------|--------------|
| `regrid_and_vert_interp` | Regrid the model's **lat/lon** climatology onto the **observation/baseline** grid, plus vertical interpolation (hybrid → pressure), so model and reference are directly comparable. *(Distinct from the SE `ncol`→lat/lon regrid — see that section.)* |

---

## `Section: analysis_scripts`
Analysis functionality. Add any of the scripts in `scripts/analysis/` directory but without the .`py` extension.

| Script | What it does |
|--------|--------------|
| `amwg_table` | Builds the AMWG summary-statistics **table**, one row per variable: global average → annual average → mean, sample size, std-dev, standard error, 5/95% confidence interval, and linear trend. |
| `aerosol_gas_tables` | **Aerosol and gaseous budget tables** (burdens/sources/sinks). Default gases `CH4, CH3CCL3, CO, O3, ISOP, MTERP, CH3OH, CH3COCH3`; aerosols `AOD, SOA, SALT, DUST, POM, BC, SO4` (set in `lib/adf_variable_defaults.yaml`). |
| `ENSO_acrossRuns` | Computes **ENSO statistics** across cases; feeds `enso_comparison_plots`. |

---

## `Section: plotting_scripts`
Plotting scripts. Add any of the scripts in `scripts/plotting/` directory but without the .`py` extension.
NIRD NOTE: Scripts marked **(NCAR obs)** have hard-code observation paths on NCAR `/glade` and
generally won't work on NIRD without those datasets. More broadly, several
scripts compare against bundled observations (e.g. `qbo`, `tape_recorder`,
`aod_latlon` use ERA5 / MLS / MODIS): **the observation data may not be present
on NIRD**, so confirm the obs are reachable before enabling these.

| Script | What it plots |
|--------|---------------|
| `global_latlon_map` | Global 2-D **lat/lon maps** of model fields with continental overlays (model vs obs/baseline). |
| `global_latlon_vect_map` | Global 2-D lat/lon maps of **vector fields** (e.g. winds) with continental overlays. |
| `global_mean_timeseries` | **Global-mean, annual-mean time series** per case on one combined plot (can include CESM2 LENS). |
| `zonal_mean` | **Zonal averages** (annual and seasonal) vs obs/baseline. |
| `meridional_mean` | **Meridional averages** (default tropical 5°S–5°N band) vs obs/baseline. |
| `polar_map` | **Polar maps** (NH or SH) of model fields with continental overlays. |
| `cam_taylor_diagram` | **Taylor diagrams** summarizing model skill. Model-vs-model only — skipped when `compare_obs: true`. |
| `qbo` | **QBO diagnostics**: 5°S–5°N zonal-mean U time series + Dunkerton–Delisi QBO amplitude, vs ERA5. |
| `ozone_diagnostics` | **Ozone** comparisons vs ozonesonde / CAM-chem observations. **(NCAR obs)** |
| `aod_latlon` | **AOD** (aerosol optical depth) lat/lon comparison vs TERRA MODIS / MERRA2. |
| `tape_recorder` | Tropical (10°S–10°N) stratospheric water-vapor **"tape recorder"** (Q vs MLS and ERA5). |
| `tem` | **TEM** (Transformed Eulerian Mean) 2-D latitude-vs-pressure maps. Needs TEM files (`cam_tem_loc`); skipped if missing. |
| `adf_histogram` | **Histograms** (distribution comparison of variables across cases). |
| `MOPITT` | CO comparison vs **MOPITT** satellite CO climatology. **(NCAR obs)** |
| `enso_comparison_plots` | **ENSO** comparison plots across simulations (uses `ENSO_acrossRuns` output). |
| `regional_map_multicase` | Regional contour maps of variables for up to 10 cases side by side. Needs the **`region_multicase`** config section (documented above). |

---

## `Section: diag_var_list`
A flat list of CAM variable names to Plot.
Notes:
- **Aerosol column burdens** (`cb_*`), **surface fluxes** (`SF*`), and **optical
  depths** (`AOD*`, `D550_*`) are *derived* — ADF auto-adds `PMID` and `T` when
  any aerosol variable is requested.
- **3-D variables** (`T`, `U`, `O3`, `RELHUM`, `CLOUD`, `OMEGA500`, …) carry a
  vertical dim and are plotted on `plot_press_levels`.
- If CVDP is run, include `PSL, TREFHT, TS, PRECT` (or `PRECC`+`PRECL`).
- Commented lines at the end of the list (e.g. `SFSO2`, `WD_*`, `DF_*`, `sum_*`)
  are examples/templates you can enable.

---

## `Section: region_multicase`
Regional multi-case maps (optional).
Custom options for the **`regional_map_multicase`** plotting script, which draws
regional contour maps of variables for **all cases (up to 10) side by side**.
Only used if `regional_map_multicase` is listed in `plotting_scripts` **and**
this section is present; otherwise it is read as `None` and skipped.

| Key | Description |
|-----|-------------|
| `region_spec` | Region box as `[slat, nlat, wlon, elon]` (south lat, north lat, west lon, east lon). |
| `region_time_option` | `calendar` → use the explicit `region_start_year`/`region_end_year`. `zeroanchor` → use `region_nyear` years starting `region_year_offset` from the beginning of the time series. |
| `region_start_year` / `region_end_year` | Year range (used when `region_time_option: calendar`). |
| `region_nyear` / `region_year_offset` | Number of years, and offset from the series start (used when `region_time_option: zeroanchor`). |
| `region_month` | Month to plot. `NULL` → fall back to `region_season`. |
| `region_season` | Season to plot. `NULL` → annual mean. |
| `region_variables` | List of variables to plot — a subset of `diag_var_list`. |

Example:
```yaml
region_multicase:
    region_spec: [-30, 30, 0, 360]      # tropics
    region_time_option: zeroanchor
    region_nyear: 10
    region_year_offset: 0
    region_month:                       # NULL -> use season
    region_season:                      # NULL -> annual mean
    region_variables:
        - PRECT
        - TS
```
