# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'chromium_tests',
  'properties',
]

def GenSteps(api):
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')

  update_step, master_dict, test_spec = \
     api.chromium_tests.sync_and_configure_build(mastername, buildername)
  #api.chromium_tests.compile(mastername, buildername, update_step, master_dict,
  #                           test_spec, out_dir='/tmp')
  api.chromium.compile(targets=['All'], out_dir='/tmp')

def GenTests(api):
  yield api.test('basic_out_dir') + api.properties(
      mastername='chromium.linux',
      buildername='Android Builder (dbg)',
      slavename='build1-a1',
      buildnumber='77457',
  )