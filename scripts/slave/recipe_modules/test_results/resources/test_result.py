# Copyright (c) 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


# See http://www.chromium.org/developers/the-json-test-results-format for
# output status types. See src/base/test/launcher/test_result.cc for input
# status types.
_GTEST_TO_TEST_RESULTS_STATUS_MAP = {
    'CRASH': 'CRASH',
    'FAILURE': 'FAIL',
    'FAILURE_ON_EXIT': 'FAIL',
    'SKIPPED': 'SKIP',
    'SUCCESS': 'PASS',
    'TIMEOUT': 'TIMEOUT',
}


def canonical_name(name):
  new_name = name.replace('FLAKY_', '', 1)
  new_name = new_name.replace('FAILS_', '', 1)
  new_name = new_name.replace('DISABLED_', '', 1)
  return new_name


def gtest_status_to_test_results_status(status):
  return _GTEST_TO_TEST_RESULTS_STATUS_MAP.get(status, 'UNKNOWN')


class TestResult(object):
  """A simple class that represents a single test result.

  This is effectively a struct used by JSONResultsGenerator. The 'status'
  field is in test-results format and 'test_run_time' is in seconds. 'modifier'
  is derived from the test's name and determines what the expected test result
  should be if it isn't expected to pass.
  """

  # Test modifier constants.
  (NONE, FAILS, FLAKY, DISABLED) = range(4)

  def __init__(self, test, status, elapsed_time=0):
    """Constructor.

    Args:
      test: String, test name.
      status: String, status is gtest format.
      elapsed_time: Number, in seconds.
    """
    self.test_name = canonical_name(test)
    self.status = gtest_status_to_test_results_status(status)
    self.failed = (self.status in ('FAIL', 'TIMEOUT', 'CRASH'))
    self.test_run_time = elapsed_time

    test_name = test
    try:
      test_name = test.split('.')[1]
    except IndexError:
      pass

    if self.status == 'SKIP':
      self.modifier = self.DISABLED
    elif test_name.startswith('FAILS_'):
      self.modifier = self.FAILS
    elif test_name.startswith('FLAKY_'):
      self.modifier = self.FLAKY
    elif test_name.startswith('DISABLED_'):
      self.modifier = self.DISABLED
    else:
      self.modifier = self.NONE

  def fixable(self):
    return self.failed or self.modifier == self.DISABLED

  def __repr__(self):
    return 'TestResult(%s, %s, %d)' % (
        self.test_name, self.status, self.test_run_time)
