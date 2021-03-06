""" Calculating the evidence and the posterior samples using the Multimodal Nested sampling method.
Multimodal nested sampling by FEROZ and HOBSON is a method built on nested sampling algorithm
by JOHN SKILLING et al for sampling through posterior with multiple modes. The method uses a loop 
where we continously replace the point in active samples which has lower likelihood with a point that
has greater likelihood. The discarded point is a posterior inference and used in calculation of evidence.
The method has the following steps:
1)Sample points from prior
2)Loop under stopping criterion
  1) Find out the point with lowest likelihood-L(i)
  2) Assign Prior mass for this iteration-X(i) 
  3) Set the values of weights using the trapezoidal rule-W(i) or calculating the information
  4) Increment the evidence by lowest_likelihood- L(i)*W(i) and store the point as posterior inference.
  5) Check stopping criterion. If converged Increment the evidence by using the active_samples too
  6) If not converged, sample a point from prior with likelihood greater than L(i)
3) After reaching maximum number of iterations Increment the evidence by using the active_samples too
4) Output the Evidence, the posterior samples and other important information 
The Difficult part in this method is sampling a new point from the prior satisfying the likelihood constraint.
According to the Multinest paper by Feroz et al. there are some methods that could help restrict the prior 
volume from which to draw a point ensuring transition between a lower iso-likelihood contour to a higher
iso-likelihood contour. The methods are :
1) Clustered ellipsoidal sampling - Builds ellipsoids around midpoints of clustered active_samples and draws
samples from these ellipsoids with a certain probability assigned to each ellipsoid.
2) Metropolis nested sampling - Uses a proposal distribution generally a symmetric gaussian distribution with a 
dispersion value which changes and drives the process to higher likelihood regions as we sample.
We are going to try both the metropolis nested sampling and clustered ellipsoidal sampling for this approach.
The Following is a class implementation of Nested_Sampler.

References:
===========
Multinest paper by Feroz and Hobson et al(2008)
Nested Sampling by John Skilling et al
http://www.inference.phy.cam.ac.uk/bayesys/
"""


import numpy as np
from math import *
import sources
from clust_ellip import *



class Nested_Sampler(object):


    """Initialization for the Nested_Sampler"""

    def __init__(self, active_samples, no_active_samples, max_iter, sample = "metropolis", plot=False, conv_thresh=0.1):
 
        """Number of active_samples in the nested sampling loop to start"""
        self.no_active_samples     = no_active_samples

        """Maximum number of iterations after which the loop is terminated"""
        self.maximum_iterations    = max_iter
        
        """ The sampling method used to draw a new sample satisfying the likelihood constraint"""
        self.sample                = sample

        """Plot posterior samples while running the loop to check how the method is working"""
        self.plot                  = plot

        """Stopping criterion for nested sample. The same value used in the Multinest paper """
        self.convergence_threshold = 0.1

        """ Sampling active points from the prior distribution specified """
        self.active_samples        = active_samples
        
        """ Variable to hold evidence at each iteration"""
        self.log_evidence              = None

        """ Posterior samples for evidence and plotting """
        self.posterior_inferences  = []

        """ Prior mass which is used to calculate the weight of the point at each iteration"""
        self.log_width             = None

        """ Information for calculating the uncertainity of calculating the evidence """
        self.Information           = None

        """ Total number of likelihood calculations""" 
        self.no_likelihood         = no_active_samples

    
    """ Method that runs the main nested sampling loop"""
    
    def fit(self):

        """ Initializing evidence and prior mass """
        self.log_evidence = -1e300
        self.log_width = log(1.0 - exp(-1.0 / self.no_active_samples))
        self.Information = 0.0
        LogL = [i.logL for i in self.active_samples]
        iteration = None
        stop = None
        prev_stop = 0.0
       
        for iteration in range(1,self.maximum_iterations):
            smallest = 0
            """Finding the object with smallest likelihood"""
            smallest = np.argmin(LogL)
            """Assigning local evidence to the smallest sample"""
            self.active_samples[smallest].logWt = self.log_width + self.active_samples[smallest].logL;
            
            largest = np.argmax(LogL)

            stop = self.active_samples[largest].logL + self.log_width - self.log_evidence

            print str(iteration)
            
            """Calculating the updated evidence"""
            temp_evidence = np.logaddexp(self.log_evidence, self.active_samples[smallest].logWt)
            
            """Calculating the information which will be helpful in calculating the uncertainity"""
            self.Information = exp(self.active_samples[smallest].logWt - temp_evidence) * self.active_samples[smallest].logL + \
            exp(self.log_evidence - temp_evidence) * (self.Information + self.log_evidence) - temp_evidence;
            
            # FIX ME : Add a stopping criterion condition 

            self.log_evidence = temp_evidence

            #print str(self.active_samples[smallest].X)+" "+str(self.active_samples[smallest].Y)+" "+str(self.active_samples[smallest].logL)
            
            sample = sources.Source()
            sample.__dict__ = self.active_samples[smallest].__dict__.copy()

            """storing posterior points"""
            self.posterior_inferences.append(sample)
            
            """New likelihood constraint""" 
            likelihood_constraint = self.active_samples[smallest].logL

            survivor = int(smallest)

            while True:
                survivor = int(self.no_active_samples * np.random.uniform(0,1)) % self.no_active_samples  # force 0 <= copy < n
                if survivor != smallest:
                    break

            if self.sample == "metropolis":
                """Obtain new sample using Metropolis principle"""
                updated, number = self.metropolis_sampling(obj = self.active_samples[survivor], LC = likelihood_constraint, likelihood_calc =self.no_likelihood)
                self.active_samples[smallest].__dict__ = updated.__dict__.copy()
                LogL[smallest] = self.active_samples[smallest].logL
                self.no_likelihood = number

            if self.sample == "clustered_ellipsoidal":
                """Obtain new sample using Clustered ellipsoidal sampling"""
                updated, number = self.clustered_sampling(active_points = self.active_samples, LC = likelihood_constraint, likelihood_calc =self.no_likelihood)
                self.active_samples[smallest].__dict__ = updated.__dict__.copy()
                LogL[smallest] = self.active_samples[smallest].logL
                self.no_likelihood = number  

            """Shrink width"""  
            self.log_width -= 1.0 / self.no_active_samples;

        # FIX ME: Incorporate the active samples into evidence calculation and information after the loop """
        """Verbose to give an idea of unique samples"""
        setz = set([i.logL for i in self.posterior_inferences ])
        print str(len(setz))
        setz = set(self.posterior_inferences)
        print str(len(setz))
        return { "src":self.active_samples,
            "samples":self.posterior_inferences, 
            "logZ":self.log_evidence,
            "Information":self.Information,
            "likelihood_calculations":self.no_likelihood,
            "iterations":self.maximum_iterations 
            }


    """ Method for drawing a new sample using the metropolis hastings principle """  

    def metropolis_sampling(self, obj, LC, likelihood_calc):
        "Instantiating the metropolis sampler object"
        Metro = Metropolis_sampler(to_evolve = obj, likelihood_constraint = LC, no =likelihood_calc )
        evolved, number = Metro.sample()
        return evolved, number


    """ Method for drawing a new sample using clustered ellipsoidal sampling"""
    
    def clustered_sampling(self, active_points, LC, likelihood_calc ):
        Clust = Clustered_Sampler(active_samples=active_points, likelihood_constraint=LC, enlargement=1.0, no=likelihood_calc)
        sample = None
        number = None
        while True:
            sample, number = Clust.sample()
            if(sample.logL > LC):
                #print "In nest: found from clustered sampling"
                break
            Clust = Clustered_Sampler(active_samples=active_points, likelihood_constraint=LC, enlargement=1.0, no=number)   
        return sample, number



class Metropolis_sampler(object):

    """Initializing metropolis sampler"""

    def __init__(self, to_evolve, likelihood_constraint, no):

        self.source = to_evolve
        self.LC     = likelihood_constraint
        self.step   = 8.0
        self.number = no
                
    """Sampling from the prior subject to constraints according to Metropolis method 
    proposed by Sivia et al discussed in Multinest paper by feroz and Hobson"""

    def sample(self):
        metro = Source()
        metro.__dict__ = self.source.__dict__.copy()
        start = Source()
        start.__dict__ = self.source.__dict__.copy()
        new   = Source()
        self.number+=1
        count = 0
        hit = 0
        miss = 0
        
        x_l, x_u = getPrior_X()
        y_l, y_u = getPrior_Y()
        r_l, r_u = getPrior_R()
        a_l, a_u = getPrior_A()

        stepnormalize = self.step/x_u

        stepX    = self.step
        stepY    = stepnormalize*(y_u-y_l)
        stepA    = stepnormalize*(a_u - a_l)
        stepR    = stepnormalize*(r_u-r_l)        
        
        bord = 1

        while(count<20):
            
            while bord==1:
                bord = 0
                new.X    = metro.X + stepX * (2.*np.random.uniform(0, 1) - 1.);
                new.Y    = metro.Y + stepY * (2.*np.random.uniform(0, 1) - 1.);
                new.A    = metro.A + stepA * (2.*np.random.uniform(0, 1) - 1.);
                new.R    = metro.R + stepR * (2.*np.random.uniform(0, 1) - 1.);

                if(new.X > x_u or new.X < x_l): bord = 1;
                if(new.Y > y_u or new.Y < y_l): bord = 1;
                if(new.A > a_u or new.A < a_l): bord = 1;
                if(new.R > r_u or new.R < r_l): bord = 1;                

            new.logL = log_likelihood(new)
            self.number+=1
            
            if(new.logL > self.LC):
                metro.__dict__ = new.__dict__.copy()
                hit+=1
            else:
                miss+=1
            
            if( hit > miss ):   self.step *= exp(1.0 / hit);
            if( hit < miss ):   self.step /= exp(1.0 / miss);

            stepnormalize = self.step/x_u         

            stepX    = self.step
            stepY    = stepnormalize*(y_u-y_l)
            stepA    = stepnormalize*(a_u - a_l)
            stepR    = stepnormalize*(r_u-r_l)        
        
            
            count+=1
            bord=1
                    
        return metro, self.number        