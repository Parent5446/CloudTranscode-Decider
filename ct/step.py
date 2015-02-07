from __future__ import absolute_import

import abc
import logging

import jinja2

_LOGGER = logging.getLogger(__name__)


class StepError(StandardError):
    pass


class StepDefinitionError(StepError):
    pass


class Step(object):

    __slots__ = ('name', 'requires')
    __metaclass__ = abc.ABCMeta

    def __init__(self, name, requires=()):
        self.name = name
        self.requires = [self._resolve_parent(parent_def)
                         for parent_def in requires]

    @staticmethod
    def _resolve_parent(parent_def):
        from .state import StepStateStatus

        if isinstance(parent_def, basestring):
            return (parent_def, StepStateStatus.succeeded)
        else:
            try:
                parent_name, status_name = parent_def
                return (parent_name, getattr(StepStateStatus, status_name))
            except AttributeError as err:
                raise StepDefinitionError('Invalid Step status name: %r' %
                                          err.args[0])
            except StandardError:
                raise StepDefinitionError('Invalid Step definition: %r' %
                                          parent_def)

    @classmethod
    def make_step(cls, step_data, activities):
        """Create a new Step object from a definition"""
        if 'activity' in step_data:
            activity_name = step_data['activity']
            activity = activities[activity_name]

            step = ActivityStep(
                name=step_data['name'],
                requires=step_data['requires'],
                activity=activity,
                input_template=step_data['input'],
            )

        elif 'eval' in step_data:
            step = TemplatedStep(
                name=step_data['name'],
                requires=step_data['requires'],
                eval_block=step_data['eval'],
            )
        return step

    @abc.abstractmethod
    def run(self, _step_input):
        pass

    @abc.abstractmethod
    def prepare(self, _context):
        pass

    @abc.abstractmethod
    def render(self, output):
        pass

    def __repr__(self):
        return '{ctype}(name={name})'.format(ctype=self.__class__.__name__,
                                             name=self.name)


class ActivityStep(Step):

    __slots__ = ('activity', 'input_template')

    def __init__(self, name, activity, input_template, requires=()):
        super(ActivityStep, self).__init__(name, requires)
        self.activity = activity
        self.input_template = jinja2.Template(input_template)

    def prepare(self, context):
        return self.input_template.render(context)

    def run(self, step_input):
        return ActivityStepResult(
            name=self.name,
            activity=self.activity,
            activity_input=step_input,
        )

    def render(self, output):
        return self.activity.render_output(output)


class ActivityStepResult(object):

    __slots__ = ('name', 'activity', 'activity_input')

    def __init__(self, name, activity, activity_input):
        self.name = name
        self.activity = activity
        self.activity_input = activity_input


class TemplatedStep(Step):

    __slots__ = ('eval_block')

    def __init__(self, name, eval_block, requires=()):
        super(TemplatedStep, self).__init__(name, requires)
        self.eval_block = jinja2.Template(eval_block)

    def prepare(self, context):
        return self.eval_block.render(context)

    def run(self, step_input):
        pass

    def render(self, _output):
        # NOTE: Templated steps do not have any usable attributes
        return {}
