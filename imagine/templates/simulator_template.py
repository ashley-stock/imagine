from imagine.simulators import Simulator
import numpy as np
import MY_SIMULATOR  # Substitute this by your own code

class SimulatorTemplate(Simulator):
    """
    Detailed description of the simulator
    """
    # The quantity that will be simulated (e.g. 'fd', 'sync', 'dm')
    # Any observable quantity absent in this list is ignored by the simulator
    SIMULATED_QUANTITIES = ['my_observable_quantity']
    # A list or set of what is required for the simulator to work
    REQUIRED_FIELD_TYPES = ['dummy', 'magnetic_field']
    # Fields which may be used if available
    OPTIONAL_FIELD_TYPES = ['thermal_electron_density']
    # One must specify which grid is compatible with this simulator
    ALLOWED_GRID_TYPES = ['cartesian']
    # Tells whether this simulator supports using different grids
    USE_COMMON_GRID = False

    def __init__(self, measurements, **extra_args):
        # Send the measurements to parent class
        super().__init__(measurements)
        # Any initialization task involving **extra_args can be done *here*
        pass

    def simulate(self, key, coords_dict, realization_id, output_units):
        """
        This is the main function you need to override to create your simulator.
        The simulator will cycle through a series of Measurements and create
        mock data using this `simulate` function for each of them.

        Parameters
        ----------
        key : tuple
            Information about the observable one is trying to simulate
        coords_dict : dictionary
            If the trying to simulate data associated with discrete positions
            in the sky, this dictionary contains arrays of coordinates.
        realization_id : int
            The index associated with the present realisation being computed.
        output_units : astropy.units.Unit
            The requested output units.
        """
        # The argument key provide extra information about the specific
        # measurement one is trying to simulate
        obs_quantity, freq_Ghz, Nside, tag = key

        # If the simulator is working on tabular data, the observed
        # coordinates can be accessed from coords_dict, e.g.
        lat, lon = coords_dict['lat'], coords_dict['lon']

        # Fields can be accessed from a dictionary stored in self.fields
        B_field_values = self.fields['magnetic_field']
        # If a dummy field is being used, instead of an actual realisation,
        # the parameters can be accessed from self.fields['dummy']
        my_dummy_field_parameters = self.fields['dummy']
        # Checklists allow _dummy fields_ to send specific information to
        # simulators about specific parameters
        checklist_params = self.field_checklist
        # Controllists in dummy fields contain a dict of simulator settings
        simulator_settings = self.controllist

        # If a USE_COMMON_GRID is set to True, the grid it can be accessed from
        # grid = self.grid

        # Otherwise, if fields are allowed to use different grids, one can
        # get the grid from the self.grids dictionary and the field type
        grid_B = self.grids['magnetic_field']

        # Finally we can _simulate_, using whichever information is needed
        # and your own MY_SIMULATOR code:
        results = MY_SIMULATOR.simulate(simulator_settings,
                                        grid_B.x, grid_B.y, grid_B.z,
                                        lat, lon, freq_Ghz, B_field_values,
                                        my_dummy_field_parameters,
                                        checklist_params)
        # The results should be in a 1-D array of size compatible with
        # your dataset. I.e. for tabular data: results.size = lat.size
        # (or any other coordinate)
        # and for HEALPix data  results.size = 12*(Nside**2)

        # Note: Awareness of other observables
        # While this method will be called for each individual observable
        # the other observables can be accessed from self.observables
        # Thus, if your simulator is capable of computing multiple observables
        # at the same time, the results can be saved to an attribute on the first
        # call of `simulate` and accessed from this cache later.
        # To break the degeneracy between multiple realisations (which will
        # request the same key), the realisation_id can be used
        # (see Hammurabi implementation for an example)
        return results
