#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Estimates capacity needs for all builders of a given master.
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
import tempfile
import urllib
import urllib2


BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_builds(mastername, buildername, days):
  results = []
  for day in days:
    cursor = ''
    while True:
      response = urllib2.urlopen(
          'https://chrome-build-extract.appspot.com/get_builds'
          '?master=%s&builder=%s&day=%s&cursor=%s' % (
              urllib.quote(mastername),
              urllib.quote(buildername),
              urllib.quote(str(day)),
              urllib.quote(cursor)))
      data = json.load(response)
      results.extend(data['builds'])
      cursor = data['cursor']
      if not cursor:
        break

  return results


def estimate_capacity(builds):
  hourly_buckets = {}
  daily_buckets = {}
  for build in builds:
    build_time = build['times'][1] - build['times'][0]

    changes = build['sourceStamp']['changes']
    if changes:
      assert len(changes) == 1
      timestamp = datetime.datetime.utcfromtimestamp(changes[0]['when'])
    else:
      # Fallback for builds that don't have blamelist/source stamp,
      # e.g. win_pgo.
      timestamp = datetime.datetime.utcfromtimestamp(build['times'][0])

    hourly_bucket = timestamp.strftime('%Y-%m-%d-%H')
    hourly_buckets.setdefault(hourly_bucket, []).append(build_time)

    daily_bucket = timestamp.strftime('%Y-%m-%d')
    daily_buckets.setdefault(daily_bucket, []).append(build_time)

  def min_bots(buckets, resolution_s):
    result = 0
    for times in buckets.itervalues():
      total_time = sum(times)
      bots = total_time / resolution_s
      result = max(result, bots)
    return result

  return {
    'hourly_bots': min_bots(hourly_buckets, 3600),
    'daily_bots': min_bots(daily_buckets, 3600 * 24),
  }


def main(argv):
  parser = argparse.ArgumentParser()
  parser.add_argument('master')
  parser.add_argument('--days', type=int, default=14)
  parser.add_argument('--ignore-cls-by', action='append')

  args = parser.parse_args(argv)

  with tempfile.NamedTemporaryFile() as f:
    subprocess.check_call([
        os.path.join(BASE_DIR, 'scripts', 'tools', 'runit.py'),
        os.path.join(BASE_DIR, 'scripts', 'tools', 'dump_master_cfg.py'),
        'masters/%s' % args.master,
        f.name])
    master_config = json.load(f)

  builder_pools = []
  for builder in master_config['builders']:
    slave_set = set(builder['slavenames'])
    builddir = builder.get('slavebuilddir', builder['name'])
    for pool in builder_pools:
      if pool['slave_set'] == slave_set:
        pool['builders'].setdefault(builddir, []).append(builder['name'])
        break
    else:
      builder_pools.append({
        'slave_set': slave_set,
        'builders': {builddir: [builder['name']]},
      })

  days = []
  for i in range(args.days):
    days.append(datetime.date.today() - datetime.timedelta(days=(i + 1)))
  for index, pool in enumerate(builder_pools):
    print 'Pool #%d:' % (index + 1)
    pool_capacity = {
      'hourly_bots': 0.0,
      'daily_bots': 0.0,
    }
    # TODO(phajdan.jr): use multiprocessing pool to speed this up.
    for builddir, builders in pool['builders'].iteritems():
      print '  builddir "%s":' % builddir
      for builder in builders:
        raw_builds = get_builds(
            args.master.replace('master.', ''), builder, days)

        builds = []
        for build in raw_builds:
          blamelist = build.get('blame', [])
          ignore_cl = False
          for entry in blamelist:
            if entry in args.ignore_cls_by:
              ignore_cl = True
              break
          if not ignore_cl:
            builds.append(build)

        capacity = estimate_capacity(builds)
        for key in ('hourly_bots', 'daily_bots'):
          pool_capacity[key] += capacity[key]
        print '    %-45s %5.1f %5.1f' % (
            builder,
            capacity['daily_bots'],
            capacity['hourly_bots'])
    print '  %-45s   %5.1f %5.1f %5.1f' % (
        'total',
        pool_capacity['daily_bots'],
        pool_capacity['hourly_bots'],
        len(pool['slave_set']))

  return 0


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
