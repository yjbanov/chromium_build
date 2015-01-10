# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

from slave import recipe_api

class GitApi(recipe_api.RecipeApi):
  _GIT_HASH_RE = re.compile('[0-9a-f]{40}', re.IGNORECASE)

  def __call__(self, *args, **kwargs):
    """Return a git command step."""
    run = kwargs.pop('run', True)
    name = kwargs.pop('name', 'git '+args[0])
    if 'cwd' not in kwargs:
      kwargs.setdefault('cwd', self.m.path['checkout'])
    git_cmd = 'git'
    if self.m.platform.is_win:
      git_cmd = self.m.path['depot_tools'].join('git.bat')
    can_fail_build = kwargs.pop('can_fail_build', True)
    try:
      return self.m.step(name, [git_cmd] + list(args), infra_step=True,
                         **kwargs)
    except self.m.step.StepFailure as f:
      if can_fail_build:
        raise
      else:
        return f.result

  def fetch_tags(self, remote_name=None, **kwargs):
    """Fetches all tags from the remote."""
    kwargs.setdefault('name', 'git fetch tags')
    remote_name = remote_name or 'origin'
    return self('fetch', remote_name, '--tags', **kwargs)

  def count_objects(self, can_fail_build=False, **kwargs):
    """Returns `git count-objects` result as a dict.

    Args:
      can_fail_build (bool): if True, may fail the build and/or raise an
        exception. Defaults to False.

    Returns:
      A dict of count-object values, or None if count-object run failed.
    """
    step_result = self(
        'count-objects', '-v', stdout=self.m.raw_io.output(),
        can_fail_build=can_fail_build, **kwargs)

    if not step_result.stdout:
      return None

    result = {}
    for line in step_result.stdout.splitlines():
      name, value = line.split(':', 1)
      try:
        result[name] = int(value.strip())
      except ValueError as ex:
        if can_fail_build:
          raise recipe_api.InfraFailure('Failed to parse output.')
        step_result.presentation.step_text = (
            'Failed to parse output.')
        step_result.presentation.status = self.m.step.WARNING
        return None

    return result

  def count_objects_delta_report(self, before, after, dest_step_result=None):
    """Reports count-objects size delta in the destination step result.

    Adds "count-objects delta" log and puts "count size delta" line to step
    text of the destination step result.

    Args:
      before (dict): result of count_objects before a change.
      after (dict): result of count_objects after a change.
      dest_step_result (StepResult): a step result that will contain the report.
        Defaults to the active step result.
    """
    assert isinstance(before, dict)
    assert isinstance(after, dict)
    dest_step_result = dest_step_result or self.m.step.active_result

    delta = {
        key: value - before[key]
        for key, value in after.iteritems()
        if key in after}
    def results_to_text(results):
      return ['  %s: %s' % (k, v) for k, v in results.iteritems()]
    dest_step_result.presentation.logs['count-objects delta'] = (
        ['before:'] + results_to_text(before) +
        ['', 'after:'] + results_to_text(after) +
        ['', 'delta:'] + results_to_text(delta)
    )

    size_delta = (
        after['size'] + after['size-pack']
        - before['size'] - before['size-pack'])
    dest_step_result.presentation.step_text
    if dest_step_result.presentation.step_text:
      dest_step_result.presentation.step_text += '\n'

    # size_delta is in KiB.
    dest_step_result.presentation.step_text += (
        'object size delta: %.2f MiB' % (size_delta / 1024.0))

  def checkout(self, url, ref=None, dir_path=None, recursive=False,
               submodules=True, keep_paths=None, step_suffix=None,
               curl_trace_file=None, can_fail_build=True,
               set_got_revision=False, remote_name=None,
               display_fetch_size=None):
    """Returns an iterable of steps to perform a full git checkout.
    Args:
      url (str): url of remote repo to use as upstream
      ref (str): ref to fetch and check out
      dir_path (Path): optional directory to clone into
      recursive (bool): whether to recursively fetch submodules or not
      submodules (bool): whether to sync and update submodules or not
      keep_paths (iterable of strings): paths to ignore during git-clean;
          paths are gitignore-style patterns relative to checkout_path.
      step_suffix (str): suffix to add to a each step name
      curl_trace_file (Path): if not None, dump GIT_CURL_VERBOSE=1 trace to that
          file. Useful for debugging git issue reproducible only on bots. It has
          a side effect of all stderr output of 'git fetch' going to that file.
      can_fail_build (bool): if False, ignore errors during fetch or checkout.
      set_got_revision (bool): if True, resolves HEAD and sets got_revision
          property.
      remote_name (str): name of the git remote to use
      display_fetch_size (bool): if True, run `git count-objects` before and
        after fetch and display delta. Adds two more steps. Defaults to False.
    """
    display_fetch_size = display_fetch_size or False
    if not dir_path:
      dir_path = url.rsplit('/', 1)[-1]
      if dir_path.endswith('.git'):  # ex: https://host/foobar.git
        dir_path = dir_path[:-len('.git')]

      # ex: ssh://host:repo/foobar/.git
      dir_path = dir_path or dir_path.rsplit('/', 1)[-1]

      dir_path = self.m.path['slave_build'].join(dir_path)

    if 'checkout' not in self.m.path:
      self.m.path['checkout'] = dir_path

    git_setup_args = ['--path', dir_path, '--url', url]

    if remote_name:
      git_setup_args += ['--remote', remote_name]
    else:
      remote_name = 'origin'

    if self.m.platform.is_win:
      git_setup_args += ['--git_cmd_path',
                         self.m.path['depot_tools'].join('git.bat')]

    step_suffix = '' if step_suffix is  None else ' (%s)' % step_suffix
    steps = [
        self.m.python(
            'git setup%s' % step_suffix,
            self.m.path['build'].join('scripts', 'slave', 'git_setup.py'),
            git_setup_args),
    ]

    # There are five kinds of refs we can be handed:
    # 0) None. In this case, we default to properties['branch'].
    # 1) A 40-character SHA1 hash.
    # 2) A fully-qualifed arbitrary ref, e.g. 'refs/foo/bar/baz'.
    # 3) A fully qualified branch name, e.g. 'refs/heads/master'.
    #    Chop off 'refs/heads' and now it matches case (4).
    # 4) A branch name, e.g. 'master'.
    # Note that 'FETCH_HEAD' can be many things (and therefore not a valid
    # checkout target) if many refs are fetched, but we only explicitly fetch
    # one ref here, so this is safe.
    fetch_args = []
    if not ref:                                  # Case 0
      fetch_remote = remote_name
      fetch_ref = self.m.properties.get('branch') or 'master'
      checkout_ref = 'FETCH_HEAD'
    elif self._GIT_HASH_RE.match(ref):        # Case 1.
      fetch_remote = remote_name
      fetch_ref = ''
      checkout_ref = ref
    elif ref.startswith('refs/heads/'):       # Case 3.
      fetch_remote = remote_name
      fetch_ref = ref[len('refs/heads/'):]
      checkout_ref = 'FETCH_HEAD'
    else:                                     # Cases 2 and 4.
      fetch_remote = remote_name
      fetch_ref = ref
      checkout_ref = 'FETCH_HEAD'

    fetch_args = [x for x in (fetch_remote, fetch_ref) if x]
    if recursive:
      fetch_args.append('--recurse-submodules')

    fetch_env = {}
    fetch_stderr = None
    if curl_trace_file:
      fetch_env['GIT_CURL_VERBOSE'] = '1'
      fetch_stderr = self.m.raw_io.output(leak_to=curl_trace_file)

    fetch_step_name = 'git fetch%s' % step_suffix
    if display_fetch_size:
      count_objects_before_fetch = self.count_objects(
          name='count-objects before %s' % fetch_step_name,
          cwd=dir_path,
          step_test_data=lambda: self.m.raw_io.test_api.stream_output(
              self.test_api.count_objects_output(1000)))
    self('retry', 'fetch', *fetch_args,
      cwd=dir_path,
      name=fetch_step_name,
      env=fetch_env,
      stderr=fetch_stderr,
      can_fail_build=can_fail_build)
    if display_fetch_size:
      count_objects_after_fetch = self.count_objects(
          name='count-objects after %s' % fetch_step_name,
          cwd=dir_path,
          step_test_data=lambda: self.m.raw_io.test_api.stream_output(
              self.test_api.count_objects_output(2000)))
      if count_objects_before_fetch and count_objects_after_fetch:
        self.count_objects_delta_report(
            count_objects_before_fetch, count_objects_after_fetch)

    self('checkout', '-f', checkout_ref,
      cwd=dir_path,
      name='git checkout%s' % step_suffix,
      can_fail_build=can_fail_build)

    if set_got_revision:
      rev_parse_step = self('rev-parse', 'HEAD',
                           cwd=dir_path,
                           name='set got_revision',
                           stdout=self.m.raw_io.output(),
                           can_fail_build=False)

      if rev_parse_step.presentation.status == 'SUCCESS':
        sha = rev_parse_step.stdout.strip()
        rev_parse_step.presentation.properties['got_revision'] = sha

    clean_args = list(self.m.itertools.chain(
        *[('-e', path) for path in keep_paths or []]))

    self('clean', '-f', '-d', '-x', *clean_args,
      name='git clean%s' % step_suffix,
      cwd=dir_path,
      can_fail_build=can_fail_build)

    if submodules:
      self('submodule', 'sync',
        name='submodule sync%s' % step_suffix,
        cwd=dir_path,
        can_fail_build=can_fail_build)
      self('submodule', 'update', '--init', '--recursive',
        name='submodule update%s' % step_suffix,
        cwd=dir_path,
        can_fail_build=can_fail_build)

  def get_timestamp(self, commit='HEAD', test_data=None, **kwargs):
    """Find and return the timestamp of the given commit."""
    step_test_data = None
    if test_data is not None:
      step_test_data = lambda: self.m.raw_io.test_api.stream_output(test_data)
    return self('show', commit, '--format=%at', '-s',
                stdout=self.m.raw_io.output(),
                step_test_data=step_test_data).stdout.rstrip()

  def rebase(self, name_prefix, branch, dir_path, remote_name=None,
             **kwargs):
    """Run rebase HEAD onto branch
    Args:
    name_prefix (str): a prefix used for the step names
    branch (str): a branch name or a hash to rebase onto
    dir_path (Path): directory to clone into
    remote_name (str): the remote name to rebase from if not origin
    """
    remote_name = remote_name or 'origin'
    try:
      self('rebase', '%s/master' % remote_name,
          name="%s rebase" % name_prefix, cwd=dir_path, **kwargs)
    except self.m.step.StepFailure:
      self('rebase', '--abort', name='%s rebase abort' % name_prefix,
          cwd=dir_path, **kwargs)
      raise
