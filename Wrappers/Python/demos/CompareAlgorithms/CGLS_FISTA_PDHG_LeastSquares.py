#========================================================================
# Copyright 2019 Science Technology Facilities Council
# Copyright 2019 University of Manchester
#
# This work is part of the Core Imaging Library developed by Science Technology
# Facilities Council and University of Manchester
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0.txt
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#=========================================================================

""" 
Compare solutions of FISTA & PDHG 
                   & CGLS  & Astra Built-in algorithms for Least Squares


Problem:     min_x || A x - g ||_{2}^{2}

             A: Projection operator
             g: Sinogram

"""


from ccpi.framework import ImageData, TestData, AcquisitionGeometry

import numpy as np 
import numpy                          
import matplotlib.pyplot as plt

from ccpi.optimisation.algorithms import PDHG, CGLS, FISTA

from ccpi.optimisation.functions import ZeroFunction, L2NormSquared, FunctionOperatorComposition
from ccpi.astra.ops import AstraProjectorSimple
import astra   
import os, sys


# Load Data 
loader = TestData(data_dir=os.path.join(sys.prefix, 'share','ccpi'))  
                     
N = 50
M = 50
data = loader.load(TestData.SIMPLE_PHANTOM_2D, size=(N,M), scale=(0,1))
ig = data.geometry

detectors = N
angles = np.linspace(0, np.pi, N, dtype=np.float32)

device = input('Available device: GPU==1 / CPU==0 ')
ag = AcquisitionGeometry('parallel','2D', angles, detectors)
if device=='1':
    dev = 'gpu'
else:
    dev = 'cpu'
    
Aop = AstraProjectorSimple(ig, ag, dev)
sin = Aop.direct(data)

noisy_data = sin 

###############################################################################
# Setup and run Astra CGLS algorithm
vol_geom = astra.create_vol_geom(N, N)
proj_geom = astra.create_proj_geom('parallel', 1.0, detectors, angles)
proj_id = astra.create_projector('linear', proj_geom, vol_geom)

# Create a sinogram from a phantom
sinogram_id, sinogram = astra.create_sino(data.as_array(), proj_id)

# Create a data object for the reconstruction
rec_id = astra.data2d.create('-vol', vol_geom)

cgls_astra = astra.astra_dict('CGLS')
cgls_astra['ReconstructionDataId'] = rec_id
cgls_astra['ProjectionDataId'] = sinogram_id
cgls_astra['ProjectorId'] = proj_id

# Create the algorithm object from the configuration structure
alg_id = astra.algorithm.create(cgls_astra)

astra.algorithm.run(alg_id, 1000)

recon_cgls_astra = astra.data2d.get(rec_id)

###############################################################################
# Setup and run the CGLS algorithm  
x_init = ig.allocate()             
cgls = CGLS(x_init=x_init, operator=Aop, data=noisy_data)
cgls.max_iteration = 1000
cgls.update_objective_interval = 200
cgls.run(1000, verbose=False)

###############################################################################
# Setup and run the PDHG algorithm 
operator = Aop
f = L2NormSquared(b = noisy_data)
g = ZeroFunction()

## Compute operator Norm
normK = operator.norm()

## Primal & dual stepsizes
sigma = 1
tau = 1/(sigma*normK**2)

pdhg = PDHG(f=f,g=g,operator=operator, tau=tau, sigma=sigma, memopt=True)
pdhg.max_iteration = 1000
pdhg.update_objective_interval = 200
pdhg.run(1000, verbose=True)

###############################################################################
# Setup and run the FISTA algorithm 
fidelity = FunctionOperatorComposition(L2NormSquared(b=noisy_data), Aop)
regularizer = ZeroFunction()

fista = FISTA(x_init=x_init , f=fidelity, g=regularizer)
fista.max_iteration = 1000
fista.update_objective_interval = 200
fista.run(1000, verbose=True)

#%% Show results

plt.figure(figsize=(10,10))
plt.suptitle('Reconstructions ', fontsize=16)

plt.subplot(2,2,1)
plt.imshow(cgls.get_output().as_array())
plt.colorbar()
plt.title('CGLS reconstruction')

plt.subplot(2,2,2)
plt.imshow(fista.get_output().as_array())
plt.colorbar()
plt.title('FISTA reconstruction')

plt.subplot(2,2,3)
plt.imshow(pdhg.get_output().as_array())
plt.colorbar()
plt.title('PDHG reconstruction')

plt.subplot(2,2,4)
plt.imshow(recon_cgls_astra)
plt.colorbar()
plt.title('CGLS astra')

diff1 = pdhg.get_output() - cgls.get_output()
diff2 = fista.get_output() - cgls.get_output()
diff3 = ImageData(recon_cgls_astra) - cgls.get_output()

plt.figure(figsize=(15,15))

plt.subplot(3,1,1)
plt.imshow(diff1.abs().as_array())
plt.title('Diff PDHG vs CGLS')
plt.colorbar()

plt.subplot(3,1,2)
plt.imshow(diff2.abs().as_array())
plt.title('Diff FISTA vs CGLS')
plt.colorbar()

plt.subplot(3,1,3)
plt.imshow(diff3.abs().as_array())
plt.title('Diff CLGS astra vs CGLS')
plt.colorbar()


#%%

print('Primal Objective (FISTA) {} '.format(fista.objective[-1]))
print('Primal Objective (CGLS) {} '.format(cgls.objective[-1]))
print('Primal Objective (PDHG) {} '.format(pdhg.objective[-1][0]))


true_obj = (Aop.direct(cglsd.get_output())-noisy_data).squared_norm()
print('True objective {}'.format(true_obj))

