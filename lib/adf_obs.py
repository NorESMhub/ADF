"""
Observations (obs) class for the Atmospheric
Diagnostics Framework (ADF).
This class inherits from the AdfInfo class.

Currently this class does three things:

1.  Initializes an instance of AdfInfo.

2.  Sets the "variable_defaults" ADF variable.

3.  Checks whether any requested variable is supposed
    to have a land or ocean mask, and if so then
    adds land and ocean fractions to the variable
    list.

4.  If a model vs obs run, then creates a
    dictionary of what observational dataset
    is associated with each requested variable,
    along with any relevant observational meta-data.

This class also provide methods for extracting
the observational data and meta-data for use
in various scripts.
"""

#++++++++++++++++++++++++++++++
#Import standard python modules
#++++++++++++++++++++++++++++++

import copy

from pathlib import Path

#+++++++++++++++++++++++++++++++++++++++++++++++++
#import non-standard python modules, including ADF
#+++++++++++++++++++++++++++++++++++++++++++++++++

import yaml

#ADF modules:
from adf_info import AdfInfo

#+++++++++++++++++++
#Define Obs class
#+++++++++++++++++++

class AdfObs(AdfInfo):

    """
    Observations class, which initializes
    an AdfInfo object and provides
    additional variables and methods
    needed for managing observational data.
    """

    def __init__(self, config_file, debug=False):

        """
        Initalize ADF Obs object.
        """

        #Initialize Config attributes:
        super().__init__(config_file, debug=debug)

        #Determine local directory:
        _adf_lib_dir = Path(__file__).parent

        # Check whether user wants to use defaults:
        #-----------------------------------------
        #Determine whether to use adf defaults or custom:
        _defaults_file = self.get_basic_info('defaults_file')
        if _defaults_file is None:
            _defaults_file = _adf_lib_dir/'adf_variable_defaults.yaml'
        else:
            print(f"\n\t Not using ADF default variables yaml file, instead using {_defaults_file}\n")
        #End if

        #Open YAML file:
        with open(_defaults_file, encoding='UTF-8') as dfil:
            self.__variable_defaults = yaml.load(dfil, Loader=yaml.SafeLoader) or {}

        # Optionally overlay a second defaults file on top of the base.  Any
        # top-level entry (variable) in the overlay REPLACES that entry in the
        # base; variables not in the overlay keep their base definition.  This
        # lets a community (e.g. NorESM) maintain only the variables that differ
        # (e.g. aerosols) instead of duplicating the entire defaults file.
        _overlay_file = self.get_basic_info('defaults_overlay_file')
        if _overlay_file is not None:
            # A bare filename is resolved against the ADF "lib" directory; an
            # absolute path is used as-is.
            _overlay_path = Path(_overlay_file)
            if not _overlay_path.is_absolute():
                _overlay_path = _adf_lib_dir / _overlay_path
            print(f"\n\t Overlaying variable defaults from {_overlay_path}\n")
            with open(_overlay_path, encoding='UTF-8') as ofil:
                _overlay = yaml.load(ofil, Loader=yaml.SafeLoader) or {}
            self.__variable_defaults.update(_overlay)

        _variable_defaults = self.__variable_defaults
        #-----------------------------------------

        #Check if land or ocean mask is requested, and if so then add OCNFRAC
        #to the variable list.  Note that this setting, and the defaults_file
        #code above, should probably be moved to AdfInfo, or somewhere else
        #farther down in the ADF inheritance chain:
        #----------------------------------------
        if self.__variable_defaults:
            #Variable defaults exist, so check if any want a land or ocean mask:
            for var in self.diag_var_list:
                #Check if any variable wants a land or ocean mask:
                if var in self.__variable_defaults:
                    if 'mask' in self.__variable_defaults[var]:
                        #Variable needs a mask, so add "OCNFRAC" to
                        #the variable list:
                        self.add_diag_var('OCNFRAC')
                        break
                   #End if
                #End if
            #End for
        #End if
        #-----------------------------------------

        #Initialize observations dictionary:
        self.__var_obs_dict = {}

        #If this is not a model vs obs run, then stop here:
        if not self.compare_obs:
            return
        #End if

        #Extract the "obs_data_loc" default observational data location:
        obs_data_loc = self.get_basic_info("obs_data_loc")

        #Optional run-level selection among multiple observational datasets:
        #a variable may list several obs under 'obs_datasets', and 'obs_source'
        #(in diag_basic_info) chooses which one to use by matching its 'obs_name'.
        #Variables with a single obs are unaffected by this setting.
        obs_source = self.get_basic_info("obs_source")

        #Loop over variable list:
        for var in self.diag_var_list:

            #Skip variables not in the defaults file:
            if var not in _variable_defaults:
                msg = f"Variable '{var}' not found in variable defaults file: `{_defaults_file}`"
                self.debug_log(msg)
                continue
            #End if
            default_var_dict = _variable_defaults[var]

            #Select which obs dataset to use for this variable (a single obs, or one
            #chosen from an 'obs_datasets' list via obs_source):
            obs_spec = self._select_obs_spec(var, default_var_dict, obs_source)
            if obs_spec is None:
                self.debug_log(f"No observations file was listed for variable '{var}'.")
                continue
            #End if

            #Locate the obs file (as given, or under obs_data_loc):
            obs_file_path = Path(obs_spec["obs_file"])
            if not obs_file_path.is_file() and obs_data_loc:
                obs_file_path = Path(obs_data_loc)/obs_file_path
            if not obs_file_path.is_file():
                msg = f'''Unable to find obs file '{obs_spec["obs_file"]}' for variable '{var}'.'''
                self.debug_log(msg)
                continue
            #End if

            #obs_name defaults to the file name; obs_var defaults to the model variable:
            obs_name = obs_spec.get("obs_name", obs_file_path.name)
            obs_var_name = obs_spec.get("obs_var_name", var)

            #Add variable to observations dictionary.  The per-obs unit conversion and
            #derivation belong to the selected dataset, so carry them here; for a
            #single (flat) obs these come from the variable-level attributes.
            self.__var_obs_dict[var] = \
                {"obs_file" : obs_file_path,
                 "obs_name" : obs_name,
                 "obs_var" : obs_var_name,
                 "obs_scale_factor" : obs_spec.get("obs_scale_factor", 1),
                 "obs_add_offset" : obs_spec.get("obs_add_offset", 0),
                 "obs_derivable_from" : obs_spec.get("obs_derivable_from"),
                 "obs_derivation_formula" : obs_spec.get("obs_derivation_formula")}

            #Copy the chosen observation's file name and variable name up to this
            #variable's top-level defaults. The plotting code labels the "Baseline"
            #panel of an obs comparison (e.g. "Baseline: ERAI_all_climo") by reading
            #'obs_file' and 'obs_var_name' from the variable's defaults. Those keys
            #used to sit at the top level but now live inside the 'obs_datasets'
            #list, so we copy the selected dataset's values back up here --
            #otherwise the plots show no observation source name.
            default_var_dict["obs_file"] = obs_file_path.name
            default_var_dict["obs_var_name"] = obs_var_name
        #End for (var)

        #If variable dictionary is still empty, then print warning to screen:
        if not self.__var_obs_dict:
            wmsg = "!!!!WARNING!!!!\n"
            wmsg += "No observations found for any variables, but this is a model vs obs run!\n"
            wmsg += "ADF will still calculate time series and climatologies if requested,"
            wmsg += " but will stop there.\n"
            wmsg += "If this result is unexpected, then run with '--debug'"
            wmsg += " and check the log for messages.\n"
            wmsg += "!!!!!!!!!!!!!!!\n"
            print(wmsg)
        #End if

    #########

    def _select_obs_spec(self, var, default_var_dict, obs_source):
        """Return the observational-dataset spec to use for a variable, or None.

        A variable may specify its observations either as a single dataset (the flat
        obs_file/obs_name/obs_var_name form) or as a list of datasets under
        'obs_datasets'.  When a list is present, the entry whose 'obs_name' matches
        the run-level 'obs_source' is chosen; if none matches (or obs_source is not
        set), the first listed entry is used.  Returns None if the variable has no
        observational dataset at all.
        """
        if "obs_datasets" in default_var_dict:
            datasets = default_var_dict["obs_datasets"]
            if not datasets:
                return None
            if obs_source is not None:
                for dset in datasets:
                    if dset.get("obs_name") == obs_source:
                        return dset
                    #End if
                #End for
                #Requested source not offered by this variable: fall back to the
                #first listed dataset, and note the substitution in the debug log.
                self.debug_log(f"obs_source '{obs_source}' not available for '{var}'; "
                               f"using '{datasets[0].get('obs_name')}' instead.")
            #End if
            return datasets[0]
        #End if
        if "obs_file" in default_var_dict:
            return default_var_dict
        #End if
        return None

    #########

    # Create property needed to return "variable_defaults" variable to user:
    @property
    def variable_defaults(self):
        """Return a copy of the '__variable_defaults' dictionary to the user if requested."""
        #Note that a copy is needed in order to avoid having a script mistakenly
        #modify this variable, as it is mutable and thus passed by reference:
        return copy.copy(self.__variable_defaults)

    # Create property needed to return "var_obs_dict" dictionary to user:
    @property
    def var_obs_dict(self):
        """Return a copy of the "var_obs_dict" list to the user if requested."""
        #Note that a copy is needed in order to avoid having a script mistakenly
        #modify this variable, as it is mutable and thus passed by reference:
        return copy.copy(self.__var_obs_dict)

#++++++++++++++++++++
#End Class definition
#++++++++++++++++++++
