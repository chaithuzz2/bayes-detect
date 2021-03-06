""" Metropolis hastings sampler to be used in Multimodal nested sampling technique
for source detection in astronomical images.

Metropolis hastings principle helps in generating a point satisfying likelihood constraint
as follows:
1.Start with a point a
2.Generate a point using a symmetric proposal distribution with a as center and a stepsize
as the dispersion. In choosing a symmetric distribution we gain the advantage of transitional
probabilities being equal.
3.Accept the point with probability min(1., priorRatio*LikelihoodRatio)
4.Since our prior is a uniform distribution in all dimensions we just accept the point if it has a
greater likelihood
5.We need to pass through the likelihood contours, Inorder to climb more likelihood levels at each iteration
We use 20 steps.  

References:
===========
Multinest paper by Feroz and Hobson et al(2008) 
Data Analysis: A Bayesian Tutorial by Sivia et al(2006)
http://en.wikipedia.org/wiki/Metropolis-Hastings_algorithm
http://www.inference.phy.cam.ac.uk/bayesys/
 """

import numpy as np
from math import *
from sources import *
import random


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