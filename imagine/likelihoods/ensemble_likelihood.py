"""
ensemble likelihood, described in IMAGINE techincal report
in principle
it combines covariance matrices from both observations and simulations
"""

# %% IMPORTS
# Built-in imports
from copy import deepcopy
import logging as log

# Package imports
import numpy as np

# IMAGINE imports
from imagine.likelihoods import Likelihood
from imagine.observables.observable_dict import Simulations
from imagine.tools.covariance_estimator import oas_mcov
from imagine.tools.parallel_ops import pslogdet, plu_solve, ptrace

# All declaration
__all__ = ['EnsembleLikelihood']


# %% CLASS DEFINITIONS
class EnsembleLikelihood(Likelihood):
    """
    EnsembleLikelihood class initialization function

    Parameters
    ----------
    measurement_dict : imagine.observables.observable_dict.Measurements
        Measurements
    covariance_dict : imagine.observables.observable_dict.Covariances
        Covariances
    mask_dict : imagine.observables.observable_dict.Masks
        Masks
    """

    def call(self, simulations_dict):
        """
        EnsembleLikelihood class call function

        Parameters
        ----------
        simulations_dict : imagine.observables.observable_dict.Simulations
            Simulations object

        Returns
        ------
        likelicache : float
            log-likelihood value (copied to all nodes)
        """
        log.debug('@ ensemble_likelihood::__call__')
        assert isinstance(simulations_dict, Simulations)
        # check dict entries
        assert  set(simulations_dict.keys()).issubset(self._measurement_dict.keys())

        likelicache = 0

        if self._covariance_dict is None:
            for name in simulations_dict.keys():
                obs_mean, obs_cov = oas_mcov(simulations_dict[name].data)  # to distributed data
                data = deepcopy(self._measurement_dict[name].data)  # to distributed data
                diff = np.nan_to_num(data - obs_mean)
                if (ptrace(obs_cov) < 1E-28):  # zero will not be reached, at most E-32
                    likelicache += -0.5*np.vdot(diff, diff)
                else:
                    sign, logdet = pslogdet(obs_cov*2*np.pi)
                    likelicache += -0.5*(np.vdot(diff, plu_solve(obs_cov, diff))+sign*logdet)
        else:
            for name in simulations_dict.keys():
                obs_mean, obs_cov = oas_mcov(simulations_dict[name].data)  # to distributed data
                data = deepcopy(self._measurement_dict[name].data)  # to distributed data
                diff = np.nan_to_num(data - obs_mean)
                if name in self._covariance_dict.keys():  # not all measurements have cov
                    full_cov = deepcopy(self._covariance_dict[name].data) + obs_cov
                    if (ptrace(full_cov) < 1E-28):  # zero will not be reached, at most E-32
                        likelicache += -0.5*np.vdot(diff, diff)
                    else:
                        sign, logdet = pslogdet(full_cov*2.*np.pi)
                        likelicache += -0.5*(np.vdot(diff, plu_solve(full_cov, diff))+sign*logdet)
                else:
                    if (ptrace(obs_cov) < 1E-28):  # zero will not be reached, at most E-32
                        likelicache += -0.5*np.vdot(diff, diff)
                    else:
                        sign, logdet = pslogdet(obs_cov*2.*np.pi)
                        likelicache += -0.5*(np.vdot(diff, plu_solve(obs_cov, diff))+sign*logdet)
        return likelicache
