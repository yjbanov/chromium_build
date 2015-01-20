# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""buildbucket module implements buildbucket-buildbot integration.

The main entry point is buildbucket.setup() that accepts master configuration
dict with other buildbucket parameters and configures master to run builds
scheduled on buildbucket service.

Example:
  buildbucket.setup(
      c,  # Configuration object.
      ActiveMaster,
      buckets=['qo'],
  )

"""

import functools
import os

from .integration import BuildBucketIntegrator
from .poller import BuildBucketPoller
from .status import BuildBucketStatus
from . import client


def setup(
    config, active_master, buckets, poll_interval=10,
    buildbucket_hostname=None, max_lease_count=None, verbose=None,
    dry_run=None):
  """Configures a master to lease, schedule and update builds on buildbucket.

  Args:
    config (dict): master configuration dict.
    active_master (config.Master.Base): master site config.
    buckets (list of str): a list of buckets to poll.
    poll_interval (int): frequency of polling, in seconds. Defaults to 10.
    buildbucket_hostname (str): if not None, override the default buildbucket
      service url.
    max_lease_count (int): maximum number of builds that can be leased at a
      time. Defaults to the number of connected slaves.
    verbose (bool): log more than usual. Defaults to False.
    dry_run (bool): whether to run buildbucket in a dry-run mode.
  """
  assert isinstance(config, dict), 'config must be a dict'
  assert active_master
  assert active_master.service_account_path, 'Service account is not assigned'
  assert buckets, 'Buckets are not specified'
  assert isinstance(buckets, list), 'Buckets must be a list'
  assert all(isinstance(b, basestring) for b in buckets), (
        'all buckets must be strings')

  if dry_run is None:
    dry_run = 'POLLER_DRY_RUN' in os.environ

  integrator = BuildBucketIntegrator(buckets, max_lease_count=max_lease_count)

  buildbucket_service_factory = functools.partial(
      client.create_buildbucket_service, active_master, buildbucket_hostname,
      verbose)

  poller = BuildBucketPoller(
      integrator=integrator,
      poll_interval=poll_interval,
      dry_run=dry_run)
  status = BuildBucketStatus(
      integrator,
      buildbucket_service_factory=buildbucket_service_factory,
      dry_run=dry_run)
  config.setdefault('change_source', []).append(poller)
  config.setdefault('status', []).append(status)
