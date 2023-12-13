from time import perf_counter as time
import os

class TSVLogger:

    def __init__(self, sub, run, ev_type, fields, dir = 'logs'):
        '''
        Opens a TSV file in which to log experiment events.

        Parameters
        ----------
        sub : str
            A subject ID.
        run : str
        ev_type : str
            The type of event we're recording in this log file
        fields : list of str
            Names of fields (columns) to be included in the log file.
        dir : str
            A relative directory path. This should be a root directory where all
            subjects' data is to be saved; a subject-specific subdirectory will
            be created within this root directory.
        '''
        dir = os.path.join(dir, 'sub-%s'%sub) # subject-level directory
        if not os.path.exists(dir):
            os.makedirs(dir)
        fpath = os.path.join(dir, 'sub-%s_run-%s_log-%s.tsv'%(sub, run, ev_type))
        self._f = open(fpath, 'w')
        self._fields = fields
        self._f.write('\t'.join(self._fields))

    def write(self, **params):
        '''
        Adds trial (meta)data to the TSV file line-by-line.

        Usage Example
        ----------
        You can write a TSV file line-by-line with the fields you specified
        when initializing the TSVLogger object.::

            log = TSVLogger(
                sub = '01', run = '01',
                ev_type = 'beh',
                fields = ['trial','resp']
                )
            log.write(trial = 1, resp = 'yes')
            log.write(trial = 2) # response will be 'n/a'

        If you don't include a field specified at initialization, then it will
        be filled in with an 'n/a' automatically.
        '''
        vals = dict()
        for field in self._fields:
            if field in params:
                vals[field] = params[field]
            else:
                vals[field] = time() if field == 'timestamp' else 'n/a'
        boilerplate = '\n' + '\t'.join(['{%s}'%key for key in self._fields])
        line = boilerplate.format(**vals)
        self._f.write(line)

    def close(self):
        self._f.close()

    def __del__(self):
        self.close()
