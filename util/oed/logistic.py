import torch
from torch.distributions.constraints import positive

import pyro
import pyro.distributions as dist
from pyro.contrib.oed.eig import marginal_eig
from pyro.infer import SVI, JitTrace_ELBO
from pyro.optim import Adam
from pyro.util import ignore_jit_warnings

from numpy.random import normal, lognormal
import numpy as np
from scipy.special import expit

def make_model(a_mean, a_sd, b_mean, b_sd):
    '''
    constructs a univariate logistic regression model with specified priors
    '''
    def model(x):
        with pyro.plate_stack("plate", x.shape[:-1]):
            a = pyro.sample("alpha", dist.LogNormal(a_mean, a_sd))
            b = pyro.sample("beta", dist.LogNormal(b_mean, b_sd))
            a = a.unsqueeze(-1)
            b = b.unsqueeze(-1)
            logit_p = b * (x - a)
            y = pyro.sample("y", dist.Bernoulli(logits = logit_p).to_event(1))
            return y
    return model

def marginal_guide(design, observation_labels, target_labels):
    # samples observations `y` in shape of design candidate tensor
    q_logit = pyro.param("q_logit", torch.zeros(design.shape[-2:]))
    pyro.sample("y", dist.Bernoulli(logits = q_logit).to_event(1))

def reparam(mean, std):
    '''
    Gives parameters of log-normal distribution with
    the desired mean and variance.
    '''
    mu = np.log(mean**2/np.sqrt(mean**2 + std**2))
    sigma2 = np.log(1 + (std**2)/(mean**2))
    sigma = np.sqrt(sigma2)
    return mu, sigma

def inverse_reparam(mu, sigma):
    mean = np.exp(mu + (sigma*sigma/2))
    var = (np.exp(sigma*sigma) - 1) * np.exp(2*mu + sigma*sigma)
    return mean, np.sqrt(var)


class LogisticOptimalDesign:

    def __init__(self, alpha_mean, alpha_scale,
                    beta_mean, beta_scale,
                    candidate_designs):
        '''
        Builds a univariate logistic regression model that can update
        online and output x's with maximal expected information gain

        candidate_designs is shape (num_candidates,), other params are floats
        '''

        # re-parametrize means for log-normal
        alpha_mu, alpha_sigma = reparam(alpha_mean, alpha_scale)
        beta_mu, beta_sigma = reparam(beta_mean, beta_scale)

        pyro.clear_param_store()
        self.amu_ = torch.tensor(alpha_mu)
        self.asd_ = torch.tensor(alpha_sigma)
        self.bmu_ = torch.tensor(beta_mu)
        self.bsd_ = torch.tensor(beta_sigma)
        self.ys = torch.tensor([])
        self.xs = torch.tensor([])
        pyro.clear_param_store()
        self._update_model()
        self._orig_model = self.current_model
        cd = np.expand_dims(candidate_designs, 1)
        self.cd_ = torch.tensor(cd)
        def guide(x):
            '''
            approximates posterior p(alpha,beta|x,y)
            '''
            with ignore_jit_warnings():
                a_mean = pyro.param("alpha_mean",
                                    torch.tensor(alpha_mu).float())
                a_sd = pyro.param("alpha_sd",
                                    torch.tensor(alpha_sigma).float(),
                                    constraint = positive)
                b_mean = pyro.param("beta_mean",
                                    torch.tensor(beta_mu).float())
                b_sd = pyro.param("beta_sd",
                                    torch.tensor(beta_sigma).float(),
                                    constraint = positive)
                pyro.sample("alpha", dist.LogNormal(a_mean, a_sd))
                pyro.sample("beta", dist.LogNormal(b_mean, b_sd))
        self.guide = guide

    def _update_model(self):
        m = make_model(self.amu_, self.asd_, self.bmu_, self.bsd_)
        self.current_model = m

    def update_model(self, x, y):
        '''
        Updates current parameter estimates given new data
        '''
        with ignore_jit_warnings():
            x = torch.tensor(x).float()
            y = torch.tensor(y)
            # use variational inference to apperoximate posterior
            self.xs = torch.cat([self.xs, x.expand(1)], dim = 0)
            self.ys = torch.cat([self.ys, y.expand(1)])
            conditioned_model = pyro.condition(self._orig_model, {"y": self.ys})

            svi = SVI(conditioned_model,
                  self.guide,
                  Adam({"lr": .005}),
                  loss = JitTrace_ELBO(),
                  #num_samples = 100
                  )
            num_iters = 500
            for i in range(num_iters):
                elbo = svi.step(self.xs)

            # update parameter estimates
            self.amu_ = pyro.param("alpha_mean").detach().clone()
            self.asd_ = pyro.param("alpha_sd").detach().clone()
            self.bmu_ = pyro.param("beta_mean").detach().clone()
            self.bsd_ = pyro.param("beta_sd").detach().clone()
            self._update_model()
            return True

    def _eig(self, num_steps = 1000, start_lr = 0.1, end_lr = 0.001):
        optimizer = pyro.optim.ExponentialLR({'optimizer': torch.optim.Adam,
                            'optim_args': {'lr': start_lr},
                            'gamma': (end_lr / start_lr) ** (1 / num_steps)})
        eig = marginal_eig(self.current_model, self.cd_, "y", ["alpha", "beta"],
                        num_samples = 100, num_steps = num_steps,
                        guide = marginal_guide, optim = optimizer,
                        final_num_samples = 10000)
        return eig

    def get_expected_information_gains(self, **kwargs):
        eig = self._eig(**kwargs).float().detach().numpy()
        eig = np.squeeze(eig)
        x = self.cd_.float().detach().numpy()
        x = np.squeeze(x)
        return x, eig

    def _posterior_predictive(self, x, samples = 1000):
        xx = np.stack([x for i in range(1000)], axis = 1)
        a = lognormal(self.amu_.numpy(), self.asd_.numpy(), samples)
        b = lognormal(self.bmu_.numpy(), self.bsd_.numpy(), samples)
        logit_p = b * (xx - a)
        return logit_p

    def posterior_predictive(self, x, **kwargs):
        logit_p = self._posterior_predictive(x, **kwargs)
        p = expit(logit_p)
        return p

    def get_probability_is_threshold(self, **kwargs):
        '''
        Returns design vector x and probability that each x is
        (nearest to) the 50/50 threshold of the response probability function
        out of the values under consideration.
        '''
        x = self.cd_.float().detach().numpy()
        x = np.squeeze(x)
        logit_p = self._posterior_predictive(x, **kwargs)
        loss = np.abs(logit_p) # p = 50% when logit(p) = 0, so loss is 0 at JND
        prob_min = (loss == loss.min(0)).mean(1) # probability each x is JND
        return x, prob_min

    def get_next_x(self, mode = 'bopt', **kwargs):
        '''
        outputs value of x that optimizes experimenter objective

        Modes:
            'oed': Bayesian optimal experimental design; maximizes
                    expected information gain on each trial.
            'bopt': Bayesian optimization; attempts to minimize
                    distance from JND-point (50% probability of each resp)
                    using Thompson Sampling.
        '''
        if mode == 'oed':
            x, eig = self.get_expected_information_gains(**kwargs)
            which_max = np.argmax(eig)
            next_x = x[which_max]
        elif mode == 'bopt':
            x, prob_5050 = self.get_probability_is_threshold(**kwargs)
            next_x = np.random.choice(x, p = prob_5050)
        else:
            raise ValueError("mode must be either 'oed' or 'bopt'!")
        return next_x

    def get_param_estimates(self):
        params = dict(
            alpha_mu = self.amu_.detach().numpy(),
            alpha_sigma = self.asd_.detach().numpy(),
            beta_mu = self.bmu_.detach().numpy(),
            beta_sigma = self.bsd_.detach().numpy(),
        )
        for p in ('alpha', 'beta'):
            mean, std = inverse_reparam(params['%s_mu'%p], params['%s_sigma'%p])
            params['%s_mean'%p] = mean
            params['%s_scale'%p] = std
        return params
