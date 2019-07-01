# -*- coding: utf-8 -*-
#   This work is part of the Core Imaging Library developed by
#   Visual Analytics and Imaging System Group of the Science Technology
#   Facilities Council, STFC

#   Copyright 2019 Edoardo Pasca

#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at

#       http://www.apache.org/licenses/LICENSE-2.0

#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
import time, functools
from numbers import Integral

class Algorithm(object):
    '''Base class for iterative algorithms

      provides the minimal infrastructure.
      Algorithms are iterables so can be easily run in a for loop. They will
      stop as soon as the stop cryterion is met.
      The user is required to implement the set_up, __init__, update and
      and update_objective methods
      
      A courtesy method run is available to run n iterations. The method accepts
      a callback function that receives the current iteration number and the actual objective
      value and can be used to trigger print to screens and other user interactions. The run
      method will stop when the stopping cryterion is met. 
   '''

    def __init__(self, **kwargs):
        '''Constructor
        
        Set the minimal number of parameters:
            iteration: current iteration number
            max_iteration: maximum number of iterations
            memopt: whether to use memory optimisation ()
            timing: list to hold the times it took to run each iteration
            update_objectice_interval: the interval every which we would save the current
                                       objective. 1 means every iteration, 2 every 2 iteration
                                       and so forth. This is by default 1 and should be increased
                                       when evaluating the objective is computationally expensive.
        '''
        self.iteration = 0
        self.__max_iteration = kwargs.get('max_iteration', 0)
        self.__loss = []
        self.memopt = False
        self.configured = False
        self.timing = []
        self._iteration = []
        self.update_objective_interval = kwargs.get('update_objective_interval', 1)
    def set_up(self, *args, **kwargs):
        '''Set up the algorithm'''
        raise NotImplementedError()
    def update(self):
        '''A single iteration of the algorithm'''
        raise NotImplementedError()
    
    def should_stop(self):
        '''default stopping cryterion: number of iterations
        
        The user can change this in concrete implementatition of iterative algorithms.'''
        return self.max_iteration_stop_cryterion()
    
    def max_iteration_stop_cryterion(self):
        '''default stop cryterion for iterative algorithm: max_iteration reached'''
        return self.iteration >= self.max_iteration
    def __iter__(self):
        '''Algorithm is an iterable'''
        return self
    def next(self):
        '''Algorithm is an iterable
        
        python2 backwards compatibility'''
        return self.__next__()
    def __next__(self):
        '''Algorithm is an iterable
        
        calling this method triggers update and update_objective
        '''
        if self.should_stop():
            self.update_objective()
            print(self.verbose_output())            
            raise StopIteration()
        else:
            time0 = time.time()
            if not self.configured:
                raise ValueError('Algorithm not configured correctly. Please run set_up.')
            if self.iteration == 0:
                self.update_objective()
                self._iteration.append(self.iteration)
                
            self.update()
            self.timing.append( time.time() - time0 )
            if self.iteration % self.update_objective_interval == 0:
                self.update_objective()
            self.iteration += 1
        
    def get_output(self):
        '''Returns the solution found'''
        return self.x
    
    def get_last_loss(self):
        '''Returns the last stored value of the loss function
        
        if update_objective_interval is 1 it is the value of the objective at the current
        iteration. If update_objective_interval > 1 it is the last stored value. 
        '''
        return self.__loss[-1]
    def get_last_objective(self):
        '''alias to get_last_loss'''
        return self.get_last_loss()
    def update_objective(self):
        '''calculates the objective with the current solution'''
        raise NotImplementedError()
    @property
    def loss(self):
        '''returns the list of the values of the objective during the iteration
        
        The length of this list may be shorter than the number of iterations run when 
        the update_objective_interval > 1
        '''
        return self.__loss
    @property
    def objective(self):
        '''alias of loss'''
        return self.loss
    @property
    def max_iteration(self):
        '''gets the maximum number of iterations'''
        return self.__max_iteration
    @max_iteration.setter
    def max_iteration(self, value):
        '''sets the maximum number of iterations'''
        assert isinstance(value, int)
        self.__max_iteration = value
    @property
    def update_objective_interval(self):
        return self.__update_objective_interval
    @update_objective_interval.setter
    def update_objective_interval(self, value):
        if isinstance(value, Integral):
            if value >= 1:
                self.__update_objective_interval = value
            else:
                raise ValueError('Update objective interval must be an integer >= 1')
        else:
            raise ValueError('Update objective interval must be an integer >= 1')
    def run(self, iterations, verbose=True, callback=None):
        '''run n iterations and update the user with the callback if specified'''
        if self.should_stop():
            print ("Stop cryterion has been reached.")
        i = 0
        if verbose:
            print (self.verbose_header())
        if self.iteration == 0:
            if verbose:
                print(self.verbose_output())
        for _ in self:
            if (self.iteration) % self.update_objective_interval == 0: 
                if verbose:
                    print (self.verbose_output())
                if callback is not None:
                    callback(self.iteration, self.get_last_objective(), self.x)
            i += 1
            if i == iterations:
                if self.iteration != self._iteration[-1]:
                    self.update_objective()
                    if verbose:
                        print (self.verbose_output())
                break

    def verbose_output(self):
        '''Creates a nice tabulated output'''
        timing = self.timing[-self.update_objective_interval-1:-1]
        self._iteration.append(self.iteration)
        if len (timing) == 0:
            t = 0
        else:
            t = sum(timing)/len(timing)
        out = "{:>9} {:>10} {:>13} {}".format(
                 self.iteration, 
                 self.max_iteration,
                 "{:.3f}".format(t), 
                 self.objective_to_string()
               )
        return out

    def objective_to_string(self):
        el = self.get_last_objective()
        if type(el) == list:
            string = functools.reduce(lambda x,y: x+' {:>13.5e}'.format(y), el[:-1],'')
            string += '{:>15.5e}'.format(el[-1])
        else:
            string = "{:>20.5e}".format(el)
        return string
    def verbose_header(self):
        el = self.get_last_objective()
        if type(el) == list:
            out = "{:>9} {:>10} {:>13} {:>13} {:>13} {:>15}\n".format('Iter', 
                                                      'Max Iter',
                                                      'Time/Iter',
                                                      'Primal' , 'Dual', 'Primal-Dual')
            out += "{:>9} {:>10} {:>13} {:>13} {:>13} {:>15}".format('', 
                                                      '',
                                                      '[s]',
                                                      'Objective' , 'Objective', 'Gap')
        else:
            out = "{:>9} {:>10} {:>13} {:>20}\n".format('Iter', 
                                                      'Max Iter',
                                                      'Time/Iter',
                                                      'Objective')
            out += "{:>9} {:>10} {:>13} {:>20}".format('', 
                                                      '',
                                                      '[s]',
                                                      '')
        return out
