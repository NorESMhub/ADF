# NorESM ADF config reference

A scannable reference for the ADF NorESM YAML config
(`config_noresm_default.yaml` / `config_noresm_default_summary.yaml`).

- **Run/edit** the bare-bones file (`config_noresm_default_summary.yaml`) — no comments, just values.
- **Look things up** here.

> Every key below lives under a top-level *section* (e.g. `diag_basic_info:`).
> Indentation and section placement matter — a key placed in the wrong section
> is silently ignored.

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
| `user` | **yes** | `mvertens` | Username; used in many default paths. `USER-NAME-NOT-SET` is the "not customized" sentinel. |
| `case` | optional | `N1850.ne30pg3...` | Convenience handle for the test case, referenced as `${case}`. |
| `nick` | optional | `noresm3_ne30_beta20` | Nickname for the test case (`${nick}`). |
| `case2` / `nick2` | optional | — | Same, for a second (baseline) case. |

---

## `diag_basic_info` — settings shared by all runs

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
| `defaults_file` | optional | `lib/adf_variable_defaults.yaml` | Custom variable-plotting defaults YAML. |
| `plot_press_levels` | optional | *(none)* | Pressure levels (hPa) for 3-D vars on lat/lon maps, e.g. `[200,500,850]`. If missing, no 3-D vars plotted on horizontal maps. |
| `central_longitude` | optional | `180` | Center longitude for lat/lon maps. |
| `num_procs` | optional | `1` | Processors for parallel steps. `"*"` = all on the node. Does **not** affect SE regrid (that runs serially). |
| `redo_plot` | optional | `false` | `true` = remake plots even if they exist. |

---

## SE (`ncol`) → lat/lon regridding — how it works

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

## `diag_cam_climo` — the case being diagnosed

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

## `diag_cam_baseline_climo` — the baseline case (only if `compare_obs: false`)

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

## `diag_cvdp_info` — Climate Variability Diagnostics Package (optional)

| Key | Default | Description |
|-----|---------|-------------|
| `cvdp_run` | `false` | Run CVDP (in background; finishes after ADF). Needs `PSL, TREFHT, TS, PRECT` (or `PRECC`+`PRECL`) in `diag_var_list`. |
| `cvdp_codebase_loc` | — | Path to the CVDP codebase. |
| `cvdp_loc` | — | Where CVDP is copied to and plots stored. |
| `cvdp_tar` | `false` | Tar up CVDP results. |

---

## `diag_mdtf_info` — NOAA MDTF diagnostics (optional, CASPER only)

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

## Script lists — which diagnostics run

Each list names scripts (without `.py`) in the corresponding `scripts/<kind>/` dir.
Pass kwargs like: `- {create_climo_files: {kwargs: {clobber: true}}}`.

| Section | Dir | Typical entries |
|---------|-----|-----------------|
| `time_averaging_scripts` | `scripts/averaging` | `create_climo_files` (`create_TEM_files` optional) |
| `regridding_scripts` | `scripts/regridding` | `regrid_and_vert_interp` |
| `analysis_scripts` | `scripts/analysis` | `amwg_table` |
| `plotting_scripts` | `scripts/plotting` | `global_mean_timeseries`, `global_latlon_map`, `global_latlon_vect_map`, `zonal_mean`, `meridional_mean`, `polar_map`, `cam_taylor_diagram`, `ozone_diagnostics`, `qbo` (`tape_recorder`, `tem` optional) |

---

## `diag_var_list` — variables to process

A flat list of CAM variable names to diagnose. Notes:

- **Aerosol column burdens** (`cb_*`), **surface fluxes** (`SF*`), and **optical
  depths** (`AOD*`, `D550_*`) are *derived* — ADF auto-adds `PMID` and `T` when
  any aerosol variable is requested.
- **3-D variables** (`T`, `U`, `O3`, `RELHUM`, `CLOUD`, `OMEGA500`, …) carry a
  vertical dim and are plotted on `plot_press_levels`.
- If CVDP is run, include `PSL, TREFHT, TS, PRECT` (or `PRECC`+`PRECL`).
- Commented lines at the end of the list (e.g. `SFSO2`, `WD_*`, `DF_*`, `sum_*`)
  are examples/templates you can enable.

---

## Minimal working example (bare-bones)

```yaml
user: 'mvertens'
case: 'n1850.ne16pg3_tn14.noresm3_0_beta21.476.2026-07-03'
nick: 'beta21_ne16'

diag_basic_info:
    hist_str: cam.h0a
    compare_obs: false
    create_html: true
    cam_regrid_loc: /scratch/${user}/noresm3/${diag_cam_climo.cam_case_name}/atm/proc/tseries/regrid
    cam_overwrite_regrid: false
    cam_se_grid: ne16                     # ne16 | ne30 | (omit to skip regridding)
    cam_se_weight_file_ne16: /nird/datalake/NS9560K/diagnostics/land_xesmf_diag_data/map_ne16pg3_to_1.9x2.5_nomask_scripgrids_c250425.nc
    cam_se_weight_file_ne30: /nird/datalake/NS9560K/diagnostics/land_xesmf_diag_data/map_ne30pg3_to_0.5x0.5_nomask_aave_da_c180515.nc
    cam_diag_plot_loc: /nird/datalake/NS2345K/www/diagnostics/ADF/${user}
    num_procs: 8
    redo_plot: true

diag_cam_climo:
    cam_case_name: ${case}
    case_nickname: ${nick}
    cam_hist_loc: /nird/datalake/NS9560K/noresm3/cases/${diag_cam_climo.cam_case_name}/atm/hist
    cam_climo_loc: /scratch/${user}/noresm3/ADF/${diag_cam_climo.cam_case_name}/atm/proc/climo
    cam_ts_loc:    /scratch/${user}/noresm3/ADF/${diag_cam_climo.cam_case_name}/atm/proc/tseries_regridded
    start_year: 960
    end_year: 969
    cam_ts_done: false
    cam_overwrite_ts: false
```
