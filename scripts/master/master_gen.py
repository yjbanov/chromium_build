# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import ast
import os

from buildbot.schedulers.basic import SingleBranchScheduler
from buildbot.status.mail import MailNotifier

from config_bootstrap import Master

from common import chromium_utils

from master import gitiles_poller
from master import master_utils
from master import slaves_list
from master.factory import annotator_factory


def PopulateBuildmasterConfig(BuildmasterConfig, builders_path,
                              master_cls=None):
  """Read builders_path and populate a build master config dict."""
  master_cls = master_cls or Master
  builders = chromium_utils.ReadBuildersFile(builders_path)
  _Populate(BuildmasterConfig, builders, master_cls)



def _Populate(BuildmasterConfig, builders, master_cls):
  classname = builders['master_classname']
  base_class = getattr(master_cls, builders['master_base_class'])
  active_master_cls = type(classname, (base_class,), {
      'buildbot_url': builders['buildbot_url'],
      'project_name': builders['master_classname'],
      'master_port': int(builders['master_port']),
      'master_port_alt': int(builders['master_port_alt']),
      'slave_port': int(builders['slave_port']),
      })

  # TODO: Modify this and the factory call, below, so that we can pass the
  # path to the builders.pyl file through the annotator to the slave so that
  # the slave can get the recipe name and the factory properties dynamically
  # without needing the master to re-read things.
  m_annotator = annotator_factory.AnnotatorFactory()

  c = BuildmasterConfig
  c['logCompressionLimit'] = False
  c['projectName'] = active_master_cls.project_name
  c['projectURL'] = master_cls.project_url
  c['buildbotURL'] = active_master_cls.buildbot_url

  # This sets c['db_url'] to the database connect string in found in
  # the .dbconfig in the master directory, if it exists. If this is
  # a production host, it must exist.
  chromium_utils.DatabaseSetup(
      c,
      require_dbconfig=active_master_cls.is_production_host)

  if builders['master_type'] == 'waterfall':
    change_source = gitiles_poller.GitilesPoller(builders['git_repo_url'])
    c['change_source'] = [change_source]
    tag_comparator = change_source.comparator
  else:
    assert builders['master_type'] == 'tryserver'
    c['change_source'] = []
    tag_comparator = None

  c['builders'] = []
  for builder_name, builder_data in builders['builders'].items():
    c['builders'].append({
        'auto_reboot': builder_data.get('auto_reboot', True),
        'name': builder_name,
        'factory': m_annotator.BaseFactory(),
        'slavebuilddir': builder_data['slavebuilddir'],
        'slavenames': chromium_utils.GetSlaveNamesForBuilder(builders,
                                                             builder_name),
    })

  c['schedulers'] = [
      SingleBranchScheduler(name='source',
                            branch='master',
                            treeStableTimer=60,
                            builderNames=[b['name'] for b in c['builders']])
  ]

  # The 'slaves' list defines the set of allowable buildslaves. List all the
  # slaves registered to a builder. Remove dupes.
  c['slaves'] = master_utils.AutoSetupSlaves(
      c['builders'],
      master_cls.GetBotPassword(),
      missing_recipients=['buildbot@chromium-build-health.appspotmail.com'])

  # This does some sanity checks on the configuration.
  slaves = slaves_list.BaseSlavesList(
      chromium_utils.GetSlavesFromBuilders(builders),
      builders['master_classname'])
  master_utils.VerifySetup(c, slaves)

  # Adds common status and tools to this master.
  # TODO: Look at the logic in this routine to see if any of the logic
  # in this routine can be moved there to simplify things.
  master_utils.AutoSetupMaster(c, active_master_cls,
      public_html='../master.chromium/public_html',
      templates=builders['templates'],
      tagComparator=tag_comparator,
      enable_http_status_push=active_master_cls.is_production_host)

  # TODO: AutoSetupMaster's settings for the following are too low to be
  # useful for most projets. We should fix that.
  c['buildHorizon'] = 3000
  c['logHorizon'] = 3000
  # Must be at least 2x the number of slaves.
  c['eventHorizon'] = 200
