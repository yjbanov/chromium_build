# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave.recipe_config import BadConf
from slave.recipe_config_types import Path
from slave import recipe_config
from RECIPE_MODULES.chromium import CONFIG_CTX


@CONFIG_CTX(group='builder')
def v8(c):
  targ_arch = c.gyp_env.GYP_DEFINES.get('target_arch')
  if not targ_arch:  # pragma: no cover
    raise recipe_config.BadConf('v8 must have a valid target_arch.')
  if c.TARGET_PLATFORM == 'android':
    c.gyp_env.GYP_DEFINES['v8_target_arch'] = 'android_' + targ_arch
  else:
    c.gyp_env.GYP_DEFINES['v8_target_arch'] = targ_arch
  del c.gyp_env.GYP_DEFINES['component']
  c.build_dir = Path('[CHECKOUT]', 'out')
  c.compile_py.build_tool = 'make'

  if c.HOST_PLATFORM == 'mac':
    c.compile_py.build_tool = 'xcode'
  elif c.HOST_PLATFORM == 'win':
    c.compile_py.build_tool = 'vs'
    c.build_dir = Path('[CHECKOUT]', 'build')

  if c.BUILD_CONFIG == 'Debug':
    c.gyp_env.GYP_DEFINES['v8_optimized_debug'] = 1
    c.gyp_env.GYP_DEFINES['v8_enable_slow_dchecks'] = 1

  # Chromium adds '_x64' to the output folder, which is neither needed nor
  # understood when compiling v8 standalone.
  if c.HOST_PLATFORM == 'win' and c.TARGET_BITS == 64:
    c.build_config_fs = c.BUILD_CONFIG
    c.compile_py.pass_arch_flag = True


@CONFIG_CTX(includes=['v8'])
def android_arm(c):
  if c.BUILD_CONFIG == 'Release':
    if c.TARGET_BITS == 64:
      c.build_config_fs = 'android_arm64.release'
    else:
      c.build_config_fs = 'android_arm.release'


@CONFIG_CTX(includes=['v8'])
def arm_hard_float(c):
  c.compile_py.pass_arch_flag = True
  c.compile_py.cross_tool = '/usr/bin/arm-linux-gnueabihf'
  c.gyp_env.GYP_DEFINES['arm_float_abi'] = 'hard'


@CONFIG_CTX(includes=['v8'])
def disassembler(c):
  c.gyp_env.GYP_DEFINES['v8_enable_disassembler'] = 1


@CONFIG_CTX(includes=['v8'])
def embed_script_mjsunit(c):
  c.gyp_env.GYP_DEFINES['embed_script'] = Path(
      '[CHECKOUT]', 'test', 'mjsunit', 'mjsunit.js')


@CONFIG_CTX(includes=['v8'])
def enable_slow_dchecks(c):
  c.gyp_env.GYP_DEFINES['v8_enable_slow_dchecks'] = 1  # pragma: no cover


@CONFIG_CTX(includes=['v8'])
def interpreted_regexp(c):
  c.gyp_env.GYP_DEFINES['v8_interpreted_regexp'] = 1


@CONFIG_CTX(includes=['v8'])
def nacl_ia32(c):
  c.gyp_env.GYP_DEFINES['v8_target_arch'] = 'nacl_ia32'  # pragma: no cover


@CONFIG_CTX(includes=['v8'])
def nacl_x64(c):
  c.gyp_env.GYP_DEFINES['v8_target_arch'] = 'nacl_x64'


@CONFIG_CTX(includes=['v8'])
def no_clang(c):
  c.gyp_env.GYP_DEFINES['clang'] = 0


@CONFIG_CTX(includes=['v8'])
def no_dcheck(c):
  c.gyp_env.GYP_DEFINES['dcheck_always_on'] = 0


@CONFIG_CTX(includes=['v8'])
def no_i18n(c):
  c.gyp_env.GYP_DEFINES['v8_enable_i18n_support'] = 0


@CONFIG_CTX(includes=['v8'])
def no_snapshot(c):
  c.gyp_env.GYP_DEFINES['v8_use_snapshot'] = 'false'


@CONFIG_CTX(includes=['v8'])
def novfp3(c):
  c.gyp_env.GYP_DEFINES['v8_can_use_vfp3_instructions'] = 'false'


@CONFIG_CTX(includes=['v8'])
def no_optimized_debug(c):
  if c.BUILD_CONFIG == 'Debug':
    c.gyp_env.GYP_DEFINES['v8_optimized_debug'] = 0


@CONFIG_CTX(includes=['v8'])
def optimized_debug(c):
  if c.BUILD_CONFIG == 'Debug':  # pragma: no cover
    c.gyp_env.GYP_DEFINES['v8_optimized_debug'] = 2


@CONFIG_CTX(includes=['v8'])
def predictable(c):
  c.gyp_env.GYP_DEFINES['v8_enable_verify_predictable'] = 1


@CONFIG_CTX(includes=['v8'])
def simulate_mipsel(c):
  if c.TARGET_BITS == 64:
    c.gyp_env.GYP_DEFINES['v8_target_arch'] = 'mips64el'
  else:
    c.gyp_env.GYP_DEFINES['v8_target_arch'] = 'mipsel'


@CONFIG_CTX(includes=['v8'])
def simulate_arm(c):
  if c.TARGET_BITS == 64:
    c.gyp_env.GYP_DEFINES['v8_target_arch'] = 'arm64'
  else:
    c.gyp_env.GYP_DEFINES['v8_target_arch'] = 'arm'


@CONFIG_CTX(includes=['v8'])
def simulate_ppc(c):
  if c.TARGET_BITS == 64:
    c.gyp_env.GYP_DEFINES['v8_target_arch'] = 'ppc64'
  else:
    c.gyp_env.GYP_DEFINES['v8_target_arch'] = 'ppc'


@CONFIG_CTX(group='compiler', includes=['v8', 'goma'])
def v8_goma(c):
  # This configuration connects the compiler group constraint with chromium's
  # goma config.
  pass


@CONFIG_CTX(includes=['v8'])
def verify_heap(c):
  c.gyp_env.GYP_DEFINES['v8_enable_verify_heap'] = 1


@CONFIG_CTX(includes=['v8'])
def vtunejit(c):
  c.gyp_env.GYP_DEFINES['v8_enable_vtunejit'] = 1


@CONFIG_CTX(includes=['v8'])
def x87(c):
  # TODO(machenbach): Chromium does not support x87 yet. With the current
  # configuration, target_arch can't be set through a parameter as ARCH=intel
  # and BITS=32 is ambigue with x87.
  c.gyp_env.GYP_DEFINES['v8_target_arch'] = 'x87'
