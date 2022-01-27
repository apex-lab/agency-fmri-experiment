import numpy as np
import pandas as pd
import os

class TSVWriter:

    def __init__(self, subj_num, dir = 'logs'):
        '''
        opens a file in which to log subject history
        '''
        self._df = None
        if not os.path.exists(dir):
            os.makedirs(dir)
        fpath = os.path.join(dir, 'subject%d.tsv'%subj_num)
        existed_already = os.path.exists(fpath)
        if existed_already: # load previous values
            self._df = pd.read_csv(fpath, sep = '\t')
            self._f = open(fpath, 'a')
        else:
            self._f = open(fpath, 'w')
            fields = ['trial_type', 'trial', 'intensity', 'latency',
                        'rt', 'pressed_first', 'agency']
            header = '\t'.join(fields)
            self._f.write(header)

    def write(self, block_name, trial_num, intensity,
                    latency, rt, pressed_first, agency):
        '''
        writes a trial's parameters to log
        '''
        line = '\n' + '\t'.join([
            block_name,
            f'{trial_num}', # int
            f'{intensity}', # in mA
            f'{latency:.2f}', # in ms
            f'{rt:.2f}', # in ms
            f'{pressed_first:d}', # boolean
            f'{agency:d}' # boolean
            ])
        self._f.write(line)

    @property
    def pretest_rts(self):
        if self._df is None:
            return []
        elif np.sum(self._df.trial_type == 'pretest') == 0:
            return []
        else:
            rts = self._df.rt[self._df.trial_type == 'pretest']
            return rts.tolist()

    @property
    def xs(self):
        if self._df is None:
            return []
        elif np.sum(self._df.trial_type == 'stimulation') == 0:
            return []
        else:
            x = self._df.latency[self._df.trial_type == 'stimulation']
            return x.tolist()

    @property
    def ys(self):
        if self._df is None:
            return []
        elif np.sum(self._df.trial_type == 'stimulation') == 0:
            return []
        else:
            y = self._df.agency[self._df.trial_type == 'stimulation']
            return y.tolist()

    @property
    def n_posttest(self):
        if self._df is None:
            return 0
        else:
            return np.sum(self._df.trial_type == 'posttest')

    @property
    def intensity(self):
        if self._df is None:
            return None
        else:
            return self._df.intensity.tolist()[0]

    def close(self):
        self._f.close()

    def __del__(self):
        self.close()
