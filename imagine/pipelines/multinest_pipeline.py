import numpy as np
import logging as log
import os
import pymultinest
from mpi4py import MPI
from imagine.pipelines.pipeline import Pipeline
from imagine.tools.icy_decorator import icy


comm = MPI.COMM_WORLD
mpisize = comm.Get_size()
mpirank = comm.Get_rank()

@icy
class MultinestPipeline(Pipeline):
    """
    Initialises Bayesian analysis pipeline with pyMultinest

    See base class for initialization details.

    Note
    ----
    Instances of this class are callable

    """
    def __call__(self, **kwargs):
        """
        Returns
        -------
        results : dict
            pyMultinest sampling results in a dictionary containing the keys:
            logZ (the log-evidence), logZerror (the error in log-evidence) and
            samples (equal weighted posterior)
        """
        log.debug('@ multinest_pipeline::__call__')

        # Checks whether a base name for multinest output files was specified
        if 'outputfiles_basename' not in self._sampling_controllers:
            # If not, uses default location
            self._sampling_controllers['outputfiles_basename'] = 'chains/imagine_'
            os.makedirs('chains', exist_ok=True)

        # Makes sure that the chains directory exists
        basedir = os.path.split(self._sampling_controllers['outputfiles_basename'])[0]
        assert os.path.isdir(basedir)
        
        # Runs pyMultinest
        results = pymultinest.solve(LogLikelihood=self._mpi_likelihood,
                                    Prior=self.prior,
                                    n_dims=len(self._active_parameters),
                                    **self._sampling_controllers)
        return results

    def _mpi_likelihood(self, cube):
        """
        mpi log-likelihood calculator
        PyMultinest supports execution with MPI
        where sampler on each node follows DIFFERENT journeys in parameter space
        but keep in communication
        so we need to firstly register parameter position on each node
        and calculate log-likelihood value of each node with joint force of all nodes
        in this way, ensemble size is multiplied by the number of working nodes

        Parameters
        ----------
        cube
            list of variable values

        Returns
        -------
        log-likelihood value
        """
        log.debug('@ multinest_pipeline::_mpi_likelihood')
        # gather cubes from all nodes
        cube_local_size = cube.size
        cube_pool = np.empty(cube_local_size*mpisize, dtype=np.float64)
        comm.Allgather([cube, MPI.DOUBLE], [cube_pool, MPI.DOUBLE])
        # calculate log-likelihood for each node
        loglike_pool = np.empty(mpisize, dtype=np.float64)
        for i in range(mpisize):  # loop through nodes
            cube_local = cube_pool[i*cube_local_size : (i+1)*cube_local_size]
            loglike_pool[i] = self._core_likelihood(cube_local)
        # scatter log-likelihood to each node
        loglike_local = np.empty(1, dtype=np.float64)
        comm.Scatter([loglike_pool, MPI.DOUBLE], [loglike_local, MPI.DOUBLE], root=0)
        return loglike_local
