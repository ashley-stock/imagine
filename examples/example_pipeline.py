# External packages 
import numpy as np
import healpy as hp
import astropy.units as u
import corner
import matplotlib.pyplot as plt
# IMAGINE
import imagine as img
import imagine.observables as img_obs
## WMAP field factories
from imagine.fields.hamx import BregLSA, BregLSAFactory
from imagine.fields.hamx import TEregYMW16, TEregYMW16Factory
from imagine.fields.hamx import CREAna, CREAnaFactory
from imagine.fields.hamx import BrndES, BrndESFactory

# Uses a RAM disk
img.rc['temp_dir'] = '/run/shm/test'


def prepare_mock_obs_data(b0=3, psi0=27, err=0.01):
    """
    Prepares fake total intensity and Faraday depth data
    
    Parameters
    ----------
    b0, psi0 : float
        "True values" in the WMAP model
    
    Returns
    -------
    mock_data : imagine.observables.observables_dict.Measurements
        Mock Measurements
    mock_cov :  imagine.observables.observables_dict.Covariances
        Mock Covariances
    """
    ## Sets the resolution
    nside=2
    size = 12*nside**2 

    # Generates the fake datasets 
    sync_dset = img_obs.SynchrotronHEALPixDataset(data=np.empty(size)*u.K, 
                                                  frequency=23, type='I')
    fd_dset = img_obs.FaradayDepthHEALPixDataset(data=np.empty(size)*u.rad/u.m**2)

    # Appends them to an Observables Dictionary
    trigger = img_obs.Measurements()
    trigger.append(dataset=sync_dset)
    trigger.append(dataset=fd_dset)

    # Prepares the Hammurabi simmulator for the mock generation
    mock_generator = img.simulators.Hammurabi(measurements=trigger)
    
    # BregLSA field
    breg_lsa = BregLSA(parameters={'b0':3, 'psi0': 27.0, 'psi1': 0.9, 'chi0': 25.0})
    # CREAna field
    cre_ana = CREAna(parameters={'alpha': 3.0, 'beta': 0.0, 'theta': 0.0,
                                 'r0': 5.0, 'z0': 1.0,
                                 'E0': 20.6, 'j0': 0.0217})
    # TEregYMW16 field
    tereg_ymw16 = TEregYMW16(parameters={})
    ## Random field
    brnd_es = BrndES(parameters={'rms': 3., 'k0': 0.5, 'a0': 1.7,
                                 'k1': 0.5, 'a1': 0.0,
                                 'rho': 0.5, 'r0': 8., 'z0': 1.},
                     grid_nx=25, grid_ny=25, grid_nz=15)
    
    ## Generate mock data (run hammurabi)
    outputs = mock_generator([breg_lsa, brnd_es, cre_ana, tereg_ymw16])
    
    ## Collect the outputs
    mockedI = outputs[('sync', '23', str(nside), 'I')].global_data[0]
    mockedRM = outputs[('fd', 'nan', str(nside), 'nan')].global_data[0]
    dm=np.mean(mockedI)
    dv=np.std(mockedI)

    ## Add some noise that's just proportional to the average sync I by the factor err
    dataI = (mockedI + np.random.normal(loc=0, scale=err*dm, size=size)) << u.K
    errorI = ((err*dm)**2) << u.K
    sync_dset = img_obs.SynchrotronHEALPixDataset(data=dataI, error=errorI,
                                                  frequency=23, type='I')
    ## Just 0.01*50 rad/m^2 of error for noise.  
    dataRM = (mockedRM + np.random.normal(loc=0, scale=err*50, 
                                          size=12*nside**2))*u.rad/u.m/u.m
    errorRM = ((err*50.)**2) << u.rad/u.m**2
    fd_dset = img_obs.FaradayDepthHEALPixDataset(data=dataRM, error=errorRM)    
    
    mock_data = img_obs.Measurements()
    mock_data.append(dataset=sync_dset)
    mock_data.append(dataset=fd_dset)

    mock_cov = img_obs.Covariances()
    mock_cov.append(dataset=sync_dset)
    mock_cov.append(dataset=fd_dset)
    
    return mock_data, mock_cov


# Creates the mock dataset
mock_data, mock_cov = prepare_mock_obs_data()

## Use an ensemble to estimate the galactic variance
likelihood = img.likelihoods.EnsembleLikelihood(mock_data, mock_cov)

## WMAP B-field, vary only b0 and psi0
breg_factory = BregLSAFactory()
breg_factory.active_parameters = ('b0', 'psi0')
breg_factory.priors = {'b0':  img.priors.FlatPrior(interval=[0., 10.]), 
                      'psi0': img.priors.FlatPrior(interval=[0., 50.])}
## Random B-field, vary only RMS amplitude
brnd_factory = BrndESFactory(grid_nx=25, grid_ny=25, grid_nz=15)
brnd_factory.active_parameters = ('rms',)
brnd_factory.priors = {'rms': img.priors.FlatPrior(interval=[0., 10.])}
## Fixed CR model
cre_factory = CREAnaFactory()
## Fixed FE model
fereg_factory = TEregYMW16Factory()

# Final Field factory list
factory_list = [breg_factory, brnd_factory, cre_factory,
                fereg_factory]

simulator = img.simulators.Hammurabi(measurements=mock_data)

pipeline = img.pipelines.MultinestPipeline(simulator=simulator, 
                                       factory_list=factory_list, 
                                       likelihood=likelihood, 
                                       ensemble_size=20)
pipeline.sampling_controllers = {'n_live_points': 100, 'verbose': True}

results=pipeline()

if mpirank == 0:
    # Reports the evidence (to file)
    with open(output_text,'w+') as f:
        f.write('log evidence: {}'.format( pipeline.log_evidence))
        f.write('log evidence error: {}'.format(pipeline.log_evidence_err))

    # Reports the posterior
    plot_results(pipeline, [a0,b0], output_file=output_file_plot)

    # Prints setup
    print('\nRC used:', img.rc)
    print('Seed used:', pipeline.master_seed)
    # Prints some results
    print('\nEvidence found:', pipeline.log_evidence, '±', pipeline.log_evidence_err)
    print('\nParameters summary:')
    for parameter in pipeline.active_parameters:
        print(parameter)
        constraints = pipeline.posterior_summary[parameter]
        for k in ['median','errup','errlo']:
            print('\t', k, constraints[k])
