"""
Correction is an abstract interface for data corrections.

Each correction has an *apply* function that takes a dataset and
updates it in place for the correction. Different kinds of
datasets support different kinds of corrections.  For
example, polarized data supports a polarized data correction
as well as the usual data corrections on the polarization
cross sections.

A correction has a string name that can be stored in a log file.

See properties.py for a discussion of correction parameters.

We may want to support an undo/redo stack, either by providing
an undo method for reversing the effect of the correction, or
by taking a snapshot of the data before the operation if the
operation is not reversable, or by rerunning all corrections
up to the current point.  We need to be careful how this
mechanism is implemented since the correction parameters
stored in the object may change over time, and since reversing
the effects of the correction may require some information about
the contents of the data.

Consider having C1(data) return a copy of the data with the
correction applied and data.apply(C1) modify the data set.

Individual corrections must inherit from Correction to support
the pipeline syntax::

    data |= normalize() | smooth() | attenuate() | ... | plot()

Unfortunately, we have to be quite careful when implementing
*correction.apply* to get the semantics just right.  We want data|filter
to return a copy of the data with the filter updates, but we don't
want to deepcopy every time.  Each filter starts with a shallow
copy of the data.  Any parts that need updating should be replaced
with the new part, not modified in place.  For example, if filter
interpolates the slit values in a slit scan, it should make a copy
of the slits before the update.  For radical changes, such as joining
or dividing datasets, a new data object can be returned.

Hopefully, these semantics will be the right balance performance and
memory usage on one hand, and convenience and intuitive feel on the other.
"""

__all__ = ['Correction']

from copy import copy
from anno_exc import annotate_exception

def _apply_and_return_data(correction, data):
    """
    Apply correction to data, returning newdata, or if recorrection is
    in place, returning data.
    """
    try:
        newdata = correction.apply(data)
    except:
        label = getattr(data, 'name', 'data')
        annotate_exception("while processing %s"%label)
        raise
    if newdata is None: newdata = data
    return newdata

class Correction(object):
    properties = []  # Property sheet for interacting with correction
    def apply(self, data):
        raise NotImplementedError

    def __str__(self):
        """
        Name of the correction, and enough detail to record in the
        reduced data log.
        """
        raise NotImplementedError

    def apply_list(self, datasets):
        """
        If the correction is called with a list of datasets, then apply the
        correction to each dataset in the list.

        Corrections such as "join" can override this, and work on the
        entire list together.
        """
        return [_apply_and_return_data(self, data) for data in datasets]

    # ==== Inherited behaviours ====
    def apply_and_log(self, data):
        #print "applying",self
        # If apply returns a new data object, forward that along, otherwise
        # assume it was an inplace update.
        if isinstance(data, list):
            data = self.apply_list(data)
        else:
            data = _apply_and_return_data(self, data)

        msg = str(self)
        if isinstance(data, list):
            for d in data: d.log(msg)
        else:
            data.log(msg)
        return data

    def __call__(self, data):
        """
        Apply the correction to the dataset, modifying the dataset
        in the process.  The data is returned, allowing users to
        apply multiple corrections in one step::

             C2(C1(data))

        Each correction will automatically be logged in the data using
        data.log(str(Correction))
        """
        return self.apply_and_log(copy(data))

    def __or__(self, other):
        if isinstance(other,Correction):
            # stage | stage: form a pipeline
            return Pipeline([self,other])
        raise NotImplementedError

    def __ror__(self, other):
        if not isinstance(other, Pipeline):
            # data | stage: apply stage to data
            return self.__call__(other)
        # pipeline | stage: handled by pipeline
        raise NotImplementedError

class Pipeline(Correction):
    def __init__(self, stages):
        self.stages = stages

    def __str__(self):
        return "|".join(str(s) for s in self.stages)

    def apply_and_log(self, data):
        for stage in self.stages:
            stage.apply_and_log(data)
        return data

    def __or__(self, other):
        if isinstance(other, Pipeline): # must be before Correction
            # pipeline | pipeline
            return Pipeline(self.stages + other.stages)
        elif isinstance(other, Correction):
            # pipeline | stage
            return Pipeline(self.stages + [other])
        else:
            raise NotImplementedError

    def __ror__(self, stage_or_data):
        if isinstance(stage_or_data, Correction):
            # stage | pipeline
            return Pipeline([stage_or_data] + self.stages)
        else:
            # data | pipeline
            self.__call__(stage_or_data)

    def __ior__(self, pipeline_or_stage):
        if isinstance(pipeline_or_stage, Pipeline): # must be before Correction
            # pipeline |= pipeline
            self.stages.extend(pipeline_or_stage.stages)
        elif isinstance(pipeline_or_stage, Correction):
            # pipeline |= stage
            self.stages.append(pipeline_or_stage)
        else:
            raise NotImplementedError
        return self

def test():
    class Add(Correction):
        def __init__(self, v): self.v = v
        def __str__(self): return "Add(%g)"%self.v
        def apply(self, data): data.x += self.v
    class Mul(Correction):
        def __init__(self, v): self.v = v
        def __str__(self): return "Mul(%g)"%self.v
        def apply(self, data):  data.x *= self.v
    class Data(object):
        x = 0
        messages = []
        def log(self, msg):
            self.messages = self.messages + [msg]
        def __or__(self, pipeline):
            return pipeline(self)
        def __ior__(self, pipeline):
            return pipeline.apply_and_log(self)

    a = Data()
    pipeline = Add(3)|Mul(2)|Add(4)
    assert a.x==0
    #print id(a),a.x
    a |= Add(1)
    #print id(a),a.x
    assert a.x == 1
    assert (a|pipeline).x == 12  # Is a copy
    assert a.x == 1 # Original is not modified
    #print id(a)
    a |= pipeline
    #print id(a)
    assert a.x == 12  # Has been modified

    a = Data() | Add(3)
    assert a.x == 3

if __name__ == "__main__":
    test()
