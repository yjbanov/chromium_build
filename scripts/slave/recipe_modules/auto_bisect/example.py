# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

DEPS = [
    'auto_bisect',
    'path',
    'properties',
    'raw_io',
    'step',
]


# This file is just a recipe showing how one would use this module.
#
# The GenSteps and GenTests functions define the required interface for a
# recipe.
#
# GenSteps is run by the recipe infrastructure and it defines the actual steps
# required to execute the recipe.
#
# GenTests yields test cases to test the recipe using the recipe infrastructure
# and it is run when executing recipe_simulation_test.py and by presubmit checks
# by git cl. Note that coverage of a 100% of the statements in the recipe and
# the recipe_modules themselves is required.
#
# More information is available in scripts/slave/README.recipes.md
def GenSteps(api):
  # Setting `api.path['checkout']` would ordinarily be done by
  # `api.chromium_tests.sync_and_configure_build`
  fake_checkout_path = api.path.mkdtemp('fake_checkout')
  api.path['checkout'] = fake_checkout_path
  bisector = api.auto_bisect.create_bisector(api.properties['bisect_config'])

  # Request builds/tests for initial range and wait
  bisector.good_rev.start_job()
  bisector.bad_rev.start_job()
  bisector.wait_for_all([bisector.good_rev, bisector.bad_rev])

  assert bisector.check_improvement_direction()
  assert bisector.check_regression_confidence()
  revisions_to_check = bisector.get_revisions_to_eval(1)
  assert len(revisions_to_check) == 1
  revisions_to_check[0].start_job()
  bisector.wait_for_any(revisions_to_check)
  bisector.check_bisect_finished(revisions_to_check[0])

  # Evaluate inserted DEPS-modified revisions
  revisions_to_check = bisector.get_revisions_to_eval(2)
  if revisions_to_check:
    revisions_to_check[0].start_job()
    revisions_to_check[0].read_deps()  # Only added for coverage.
  else:
    raise api.step.StepFailure('Expected revisions to check.')
  # TODO(robertocn): Add examples for the following operations
  # Abort unnecesary jobs # Print results


def GenTests(api):
  basic_data = _get_basic_test_data()
  yield _make_test(api, basic_data, 'basic')

  reversed_basic_data = _get_reversed_basic_test_data()
  yield _make_test(api, reversed_basic_data, 'reversed_basic')

  bad_git_hash_data = _get_basic_test_data()
  bad_git_hash_data[1]['interned_hashes'] = {'003': '12345', '002': 'Bad Hash'}
  yield _make_test(api, bad_git_hash_data, 'failed_git_hash_object')

  missing_dep_data = _get_basic_test_data()
  tricked_DEPS_file = ("vars={'v8_' + 'revision': '001'};"
                       "deps = {'src/v8': 'v8.git@' + Var('v8_revision'),"
                       "'src/third_party/WebKit': 'webkit.git@010'}")
  missing_dep_data[0]['DEPS'] = tricked_DEPS_file
  yield _make_test(api, missing_dep_data, 'missing_vars_entry')

  missing_dep_data = _get_basic_test_data()
  tricked_DEPS_file = ("vars={'v8_revision': '001'};"
                       "deps = {'src/v8': 'v8.XXX@' + Var('v8_revision'),"
                       "'src/third_party/WebKit': 'webkit.git@010'}")
  missing_dep_data[0]['DEPS'] = tricked_DEPS_file
  yield _make_test(api, missing_dep_data, 'missing_deps_entry')

  bad_deps_syntax_data = _get_basic_test_data()
  bad_deps_syntax_data[1]['DEPS']='raise RuntimeError("")'
  yield _make_test(api, bad_deps_syntax_data, 'bad_deps_syntax')


def _get_basic_test_data():
  return [
      {
          'hash': 'a6298e4afedbf2cd461755ea6f45b0ad64222222',
          'commit_pos': '314015',
          'test_results': {
              'results':{
                  'mean': 20,
                  'std_err': 1,
                  'values': [19, 20, 21],
              }
          },
          "DEPS": ("vars={'v8_revision': '001'};"
                   "deps = {'src/v8': 'v8.git@' + Var('v8_revision'),"
                   "'src/third_party/WebKit': 'webkit.git@010'}"),
          'git_diff': {
              '002': 'Dummy .diff contents 001 - 002',
              '003': 'Dummy .diff contents 001 - 003',
          },
      },
      {
          'hash': 'dcdcdc0ff1122212323134879ddceeb1240b0988',
          'commit_pos': '314016',
          'test_results': {
              'results':{
                  'mean': 15,
                  'std_err': 1,
                  'values': [14, 15, 16],
              }
          },
          'DEPS_change': 'True',
          "DEPS": ("vars={'v8_revision': '004'};"
                   "deps = {'src/v8': 'v8.git@' + Var('v8_revision'),"
                   "'src/third_party/WebKit': 'webkit.git@010'}"),
          'DEPS_interval': {'v8': '004 003 002'.split()},
      },
      {
          'hash': '00316c9ddfb9d7b4e1ed2fff9fe6d964d2111111',
          'commit_pos': '314017',
          'test_results': {
              'results':{
                  'mean': 15,
                  'std_err': 1,
                  'values': [14, 15, 16],
              }
          }
      },
  ]


def _get_reversed_basic_test_data():
  return [
      {
          'hash': '00316c9ddfb9d7b4e1ed2fff9fe6d964d2111111',
          'commit_pos': '314015',
          'test_results': {
              'results':{
                  'mean': 20,
                  'std_err': 1,
                  'values': [19, 20, 21],
              }
          }
      },
      {
          'hash': 'a6298e4afedbf2cd461755ea6f45b0ad64222222',
          'commit_pos': '314016',
          'test_results': {
              'results':{
                  'mean': 20,
                  'std_err': 1,
                  'values': [19, 20, 21],
              }
          },
          "DEPS": ("vars={'v8_revision': '001'};"
                   "deps = {'src/v8': 'v8.git@' + Var('v8_revision'),"
                   "'src/third_party/WebKit': 'webkit.git@010'}"),
          'git_diff': {
              '002': 'Dummy .diff contents 001 - 002',
              '003': 'Dummy .diff contents 001 - 003',
          },
      },
      {
          'hash': 'dcdcdc0ff1122212323134879ddceeb1240b0988',
          'commit_pos': '314017',
          'test_results': {
              'results':{
                  'mean': 15,
                  'std_err': 1,
                  'values': [14, 15, 16],
              }
          },
          'DEPS_change': 'True',
          "DEPS": ("vars={'v8_revision': '004'};"
                   "deps = {'src/v8': 'v8.git@' + Var('v8_revision'),"
                   "'src/third_party/WebKit': 'webkit.git@010'}"),
          'DEPS_interval': {'v8': '004 003 002'.split()},
      },
  ]


def _make_test(api, test_data, test_name):
  basic_test =  api.test(test_name)
  for revision_data in test_data:
    for step_data in _get_step_data_for_revision(api, revision_data):
      basic_test += step_data
  basic_test += api.properties(bisect_config=_get_default_config())
  return basic_test


def _get_default_config():
  example_config = {
      'test_type':'perf',
      'command':
          ('src/tools/perf/run_benchmark -v --browser=release smoothness.'
           'tough_scrolling_cases'),
      'good_revision': '314015',
      'bad_revision': '314017',
      'metric': 'mean_input_event_latency/mean_input_event_latency',
      'repeat_count': '2',
      'max_time_minutes': '5',
      'truncate_percent': '0',
      'bug_id': '',
      'gs_bucket': 'chrome-perf',
      'builder_host': 'master4.golo.chromium.org',
      'builder_port': '8341',
      'dummy_builds': 'True',
      'skip_gclient_ops': 'True',
  }
  return example_config


def _get_step_data_for_revision(api, revision_data, include_build_steps=True):
  """Generator that produces step patches for fake results."""
  commit_pos = revision_data['commit_pos']
  commit_hash = revision_data['hash']
  test_results = revision_data['test_results']

  step_name = 'resolving commit_pos ' + commit_pos
  yield api.step_data(step_name, stdout=api.raw_io.output('hash:' +
                                                          commit_hash))

  step_name = 'resolving hash ' + commit_hash
  commit_pos_str = 'refs/heads/master@{#%s}' % commit_pos
  yield api.step_data(step_name, stdout=api.raw_io.output(commit_pos_str))

  if include_build_steps:
    step_name = 'gsutil Get test results for build ' + commit_hash
    yield api.step_data(step_name, stdout=api.raw_io.output(json.dumps(
        test_results)))

    step_name = 'Get test status for build ' + commit_hash
    yield api.step_data(step_name, stdout=api.raw_io.output('Complete'))

    step_name = 'gsutil Get test status url for build ' + commit_hash
    yield api.step_data(step_name, stdout=api.raw_io.output('dummy/url'))

    if revision_data.get('DEPS', False):
      step_name = 'git cat-file %s:DEPS' % commit_hash
      yield api.step_data(step_name, stdout=api.raw_io.output(
          revision_data['DEPS']))

    if 'git_diff' in revision_data:
      for deps_rev, diff_file in revision_data['git_diff'].iteritems():
        step_name = 'Generating patch for %s:DEPS to %s'
        step_name %= (commit_hash, deps_rev)
        yield api.step_data(step_name, stdout=api.raw_io.output(diff_file))

    if 'DEPS_change' in revision_data:
      step_name = 'Checking DEPS for ' + commit_hash
      yield api.step_data(step_name, stdout=api.raw_io.output('DEPS'))

    if 'DEPS_interval' in revision_data:
      for depot_name, interval in revision_data['DEPS_interval'].iteritems():
        for item in interval[1:]:
          step_name = 'Hashing modified DEPS file with revision ' + item
          file_hash = 'f412e8458'
          if 'interned_hashes' in revision_data:
            file_hash = revision_data['interned_hashes'][item]
          yield api.step_data(step_name, stdout=api.raw_io.output(file_hash))
        step_name = 'Expanding revision range for revision %s on depot %s'
        step_name %= (interval[0], depot_name)
        stdout = api.raw_io.output('\n'.join(interval))
        yield api.step_data(step_name, stdout=stdout)

