# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api
from recipe_engine import util as recipe_util

from .util import GTestResults, TestResults

# TODO(luqui): Destroy this DEPS hack.
import DEPS
JsonOutputPlaceholder = DEPS['json'].api.JsonOutputPlaceholder

class TestResultsOutputPlaceholder(JsonOutputPlaceholder):
  def result(self, presentation, test):
    ret = super(TestResultsOutputPlaceholder, self).result(presentation, test)
    return TestResults(ret)


# TODO(martiniss) replace this with step.AggregateResults once
# aggregate steps lands
class GTestResultsOutputPlaceholder(JsonOutputPlaceholder):
  def result(self, presentation, test):
    ret = super(GTestResultsOutputPlaceholder, self).result(presentation, test)
    return GTestResults(ret)

class TestUtilsApi(recipe_api.RecipeApi):
  @staticmethod
  def format_step_text(data):
    """
    Returns string suitable for use in a followup function's step result's
    presentation step text.

    Args:
      data - iterable of sections, where each section is one of:
        a) tuple/list with one element for a single-line section
           (always displayed)
        b) tuple/list with two elements where first one is the header,
           and the second one is an iterable of content lines; if there are
           no contents, the whole section is not displayed
    """
    step_text = []
    for section in data:
      if len(section) == 1:
        # Make it possible to display single-line sections.
        step_text.append('<br/>%s<br/>' % section[0])
      elif len(section) == 2:
        # Only displaying the section (even the header) when it's non-empty
        # simplifies caller code.
        if section[1]:
          step_text.append('<br/>%s<br/>' % section[0])
          step_text.extend(('%s<br/>' % line for line in section[1]))
      else:  # pragma: no cover
        raise ValueError(
            'Expected a one or two-element list, got %r instead.' % section)
    return ''.join(step_text)

  # TODO(martinis) rewrite this. can be written better using 1.5 syntax.
  # TODO(phajdan.jr): Deduplicate this and chromium_tests.create_test_runner.
  def run_tests(self, caller_api, tests, suffix, test_filters=None):
    """
    Utility function for running a list of tests and returning the failed tests.

    Args:
      caller_api - caller's recipe API; this is needed because self.m here
                   is different than in the caller (different recipe modules
                   get injected depending on caller's DEPS vs. this module's
                   DEPS)
      tests - iterable of objects implementing the Test interface above
      suffix - custom suffix, e.g. "with patch", "without patch" indicating
               context of the test run
      test_filters - a dict mapping test full name to a list of tests, e.g.:
                     {
                       'base_unittests on Windows-XP-SP3': [
                         'suite11.test1',
                         'suite12.test2'
                       ],
                       'browser_tests on Windows-XP-SP3': [
                         'suite21.test1',
                         'suite22.test2'
                       ],
                     }

    Returns:
      The list of failed tests.
    """
    failed_tests = []
    test_filters = test_filters or {}

    #TODO(martiniss) convert loops
    for t in tests:
      try:
        t.pre_run(caller_api, suffix, test_filter=test_filters.get(t.name))
      # TODO(iannucci): Write a test.
      except caller_api.step.InfraFailure:  # pragma: no cover
        raise
      except caller_api.step.StepFailure:  # pragma: no cover
        failed_tests.append(t)

    for t in tests:
      try:
        t.run(caller_api, suffix, test_filter=test_filters.get(t.name))
      except caller_api.step.InfraFailure:  # pragma: no cover
        raise
      # TODO(iannucci): How should exceptions be accumulated/handled here?
      except caller_api.step.StepFailure:
        failed_tests.append(t)

    for t in tests:
      try:
        t.post_run(caller_api, suffix, test_filter=test_filters.get(t.name))
      # TODO(iannucci): Write a test.
      except caller_api.step.InfraFailure:  # pragma: no cover
        raise
      except caller_api.step.StepFailure:  # pragma: no cover
        failed_tests.append(t)

    return failed_tests

  def run_tests_with_patch(self, caller_api, tests):
    self.run_tests(caller_api, tests, 'with patch')

    failing_tests = []
    with self.m.step.defer_results():
      for t in tests:
        if not t.has_valid_results(caller_api, 'with patch'):
          self._invalid_test_results(t)
        elif t.failures(caller_api, 'with patch'):
          failing_tests.append(t)
    return failing_tests

  def determine_new_failures(self, caller_api, tests, deapply_patch_fn):
    """
    Utility function for running steps with a patch applied, and retrying
    failing steps without the patch. Failures from the run without the patch are
    ignored.

    Args:
      caller_api - caller's recipe API; this is needed because self.m here
                   is different than in the caller (different recipe modules
                   get injected depending on caller's DEPS vs. this module's
                   DEPS)
      tests - iterable of objects implementing the Test interface above
      deapply_patch_fn - function that takes a list of failing tests
                         and undoes any effect of the previously applied patch
    """
    # Convert iterable to list, since it is enumerated multiple times.
    tests = list(tests)

    failing_tests = self.run_tests_with_patch(caller_api, tests)
    if not failing_tests:
      return

    try:
      result = deapply_patch_fn(failing_tests)
      self.run_tests(caller_api, failing_tests, 'without patch')
      return result
    finally:
      with self.m.step.defer_results():
        for t in failing_tests:
          self._summarize_retried_test(caller_api, t)

  def _invalid_test_results(self, test):
    self.m.tryserver.set_invalid_test_results_tryjob_result()
    self.m.python.failing_step(test.name, 'TEST RESULTS WERE INVALID')

  def _summarize_retried_test(self, caller_api, test):
    """Summarizes test results and exits with a failing status if there were new
    failures."""
    if not test.has_valid_results(caller_api, 'without patch'):
      self._invalid_test_results(test)

    ignored_failures = set(test.failures(caller_api, 'without patch'))
    new_failures = (
      set(test.failures(caller_api, 'with patch')) - ignored_failures)

    self.m.tryserver.add_failure_reason({
      'test_name': test.name,
      'new_failures': sorted(new_failures),
    })

    step_name = '%s (retry summary)' % test.name
    step_text = self.format_step_text([
        ['failures:', new_failures],
        ['ignored:', ignored_failures]
    ])
    try:
      if new_failures:
        self.m.python.failing_step(step_name, step_text)
      else:
        self.m.python.succeeding_step(step_name, step_text)
    finally:
      if new_failures:
        self.m.tryserver.set_test_failure_tryjob_result()
      elif ignored_failures:
        self.m.step.active_result.presentation.status = self.m.step.WARNING

  @recipe_util.returns_placeholder
  def test_results(self, add_json_log=True):
    """A placeholder which will expand to '/tmp/file'.

    The recipe must provide the expected --json-test-results flag.

    The test_results will be an instance of the TestResults class.
    """
    return TestResultsOutputPlaceholder(self, add_json_log)

  @recipe_util.returns_placeholder
  def gtest_results(self, add_json_log=True):
    """A placeholder which will expand to
    '--test-launcher-summary-output=/tmp/file'.

    Provides the --test-launcher-summary-output flag since --flag=value
    (i.e. a single token in the command line) is the required format.

    The test_results will be an instance of the GTestResults class.
    """
    return GTestResultsOutputPlaceholder(self, add_json_log)

