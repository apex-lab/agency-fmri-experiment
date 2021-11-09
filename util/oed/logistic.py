import torch
from torch.distributions.constraints import positive

import pyro
import pyro.distributions as dist
from pyro.contrib.oed.eig import marginal_eig
from pyro.infer import SVI, Trace_ELBO
from pyro.optim import Adam

def make_model(a_mean, a_sd, b_mean, b_sd):
    '''
    constructs a univariate logistic regression model with specified priors
    '''
    def model(x):
        with pyro.plate_stack("plate", x.shape[:-1]):
            a = pyro.sample("alpha", dist.Normal(a_mean, a_sd))
            b = pyro.sample("beta", dist.Normal(b_mean, b_sd))
            logit_p = a + b*x
            y = pyro.sample("y", dist.Bernoulli(logits = logit_p).to_event(1))
            return y
    return model

def marginal_guide(design, observation_labels, target_labels):
    # samples observations `y` in shape of design candidate tensor
    q_logit = pyro.param("q_logit", torch.zeros(design.shape[-2:]))
    pyro.sample("y", dist.Bernoulli(logits = q_logit).to_event(1))

class LogisticOptimalDesign:

    def __init__(self, alpha_mean, alpha_sd,
                    beta_mean, beta_sd,
                    candidate_designs):
        '''
        Builds a univariate logistic regression model that can update
        online and output x's with maximal expected information gain

        candidate_designs is shape (num_candidates, 1), other params are floats
        '''
        self.amu_ = torch.tensor(alpha_mean)
        self.asd_ = torch.tensor(alpha_sd)
        self.bmu_ = torch.tensor(beta_mean)
        self.bsd_ = torch.tensor(beta_sd)
        self.ys = torch.tensor([])
        self.xs = torch.tensor([])
        pyro.clear_param_store()
        self._update_model()
        self._orig_model = self.current_model
        self.cd_ = torch.tensor(candidate_designs)
        def guide(x):
            '''
            approximates posterior p(alpha,beta|x,y)
            '''
            a_mean = pyro.param("alpha_mean", alpha_mean.clone())
            a_sd = pyro.param("alpha_sd", alpha_sd.clone(),
                                        constraint = positive)
            b_mean = pyro.param("beta_mean", beta_mean.clone())
            b_sd = pyro.param("beta_sd", beta_sd.clone(),
                                        constraint = positive)
            pyro.sample("alpha", dist.Normal(a_mean, a_sd))
            pyro.sample("beta", dist.Normal(b_mean, b_sd))
        self.guide = guide

    def _update_model(self):
        m = make_model(self.amu_, self.asd_, self.bmu_. self.bsd_)
        self.current_model = m

    def update_model(self, x, y):
        '''
        Updates current parameter estimates given new data
        '''
        x = torch.tensor(x)
        y = torch.tensor(y)
        # use variational inference to apperoximate posterior
        self.xs = torch.cat([self.xs, x], dim = 0)
        self.ys = torch.cat([self.ys, y.expand(1)])
        conditioned_model = pyro.condition(self._orig_model, {"y": ys})
        svi = SVI(conditioned_model,
              guide,
              Adam({"lr": .005}),
              loss = Trace_ELBO(),
              num_samples = 100)
        num_iters = 2000
        for i in range(num_iters):
            elbo = svi.step(xs)

        # update parameter estimates
        self.amu_ = pyro.param("alpha_mean").detach().clone()
        self.asd_ = pyro.param("alpha_sd").detach().clone()
        self.bmu_ = pyro.param("beta_mean").detach().clone()
        self.bsd_ = pyro.param("beta_sd").detach().clone()
        self._update_model()


    def get_next_x(self, num_steps = 1000, start_lr = 0.1, end_lr = 0.001):
        '''
        outputs value of x with greatest expected information gain
        '''
        optimizer = pyro.optim.ExponentialLR({'optimizer': torch.optim.Adam,
                            'optim_args': {'lr': start_lr},
                            'gamma': (end_lr / start_lr) ** (1 / num_steps)})
        eig = marginal_eig(self.current_model, self.cd_, "y", ["alpha", "beta"],
                        num_samples = 100, num_steps = num_steps,
                        guide = marginal_guide, optim = optimizer,
                        final_num_samples = 10000)
        best_x = torch.argmax(eig).float().detach().numpy()
        return best_x
