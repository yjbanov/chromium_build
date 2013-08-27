# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class WebRTCFYI(Master.Master3):
  project_name = 'WebRTC FYI'
  master_port = 8063
  slave_port = 8163
  master_port_alt = 8263
  server_url = 'http://webrtc.googlecode.com'
  project_url = 'http://webrtc.googlecode.com'
  from_address = 'webrtc-cb-fyi-watchlist@google.com'
  permitted_domains = ('google.com', 'chromium.org', 'webrtc.org')
