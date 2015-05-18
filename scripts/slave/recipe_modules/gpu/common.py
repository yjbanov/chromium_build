# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

GPU_ISOLATES = (
  'angle_unittests',
  'content_gl_tests',
  'gl_tests',
  'gles2_conform_test',
  'gpu_unittests',
  'tab_capture_end2end_tests',
  'telemetry_gpu_test',
)

# Until the media-only tests are extracted from content_unittests and
# these both can be run on the commit queue with
# --require-audio-hardware-for-testing, run them only on the FYI
# waterfall.
FYI_ONLY_GPU_ISOLATES = (
  'audio_unittests',
  'content_unittests',
)

# This will be folded into the list above once ANGLE is running on all
# platforms.
WIN_ONLY_GPU_ISOLATES = (
  'angle_end2end_tests',
)
