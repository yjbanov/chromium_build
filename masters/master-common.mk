# -*- makefile -*-

# This should be included by a makefile which lives in a buildmaster/buildslave
# directory (next to the buildbot.tac file). That including makefile *must*
# define MASTERPATH.

# The 'start' and 'stop' targets start and stop the buildbot master.
# The 'reconfig' target will tell a buildmaster to reload its config file.

# Note that a relative PYTHONPATH entry is relative to the current directory.

# Confirm that MASTERPATH has been defined.
ifeq ($(MASTERPATH),)
  $(error MASTERPATH not defined.)
endif

# On the Mac, the buildbot is started via the launchd mechanism as a
# LaunchAgent to give the slave a proper Mac UI environment for tests.  In
# order for this to work, the plist must be present and loaded by launchd, and
# the user must be logged in to the UI.  The plist is loaded by launchd at user
# login (and the job may have been initially started at that time too).  Our
# Mac build slaves are all set up this way, and have auto-login enabled, so
# "make start" should just work and do the right thing.
#
# When using launchd to start the job, it also needs to be used to stop the
# job.  Otherwise, launchd might try to restart the job when stopped manually
# by SIGTERM.  Using SIGHUP for reconfig is safe with launchd.
#
# Because it's possible to have more than one slave on a machine (for testing),
# this tests to make sure that the slave is in the known slave location,
# /b/slave, which is what the LaunchAgent operates on.
USE_LAUNCHD := \
  $(shell [ -f ~/Library/LaunchAgents/org.chromium.buildbot.$(MASTERPATH).plist ] && \
          [ "$$(pwd -P)" = "/b/build/masters/$(MASTERPATH)" ] && \
          echo 1)

start:
ifneq ($(USE_LAUNCHD),1)
	PYTHONPATH=../../third_party/buildbot_7_12:../../third_party/twisted_8_1:../../scripts:../../third_party:../../site_config:../../../build_internal/site_config:. python ../../scripts/common/twistd --no_save -y buildbot.tac
else
	echo launchctl start org.chromium.buildbot.$(MASTERPATH)
endif

stop:
ifneq ($(USE_LAUNCHD),1)
	if `test -f twistd.pid`; then kill `cat twistd.pid`; fi;
else
	echo launchctl stop org.chromium.buildbot.$(MASTERPATH)
endif

reconfig:
	kill -HUP `cat twistd.pid`

log:
	tail -F twistd.log

wait:
	while `test -f twistd.pid`; do sleep 1; done;

restart: stop wait start log
