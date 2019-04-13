"""
A Sublime Text 2/3 plugin for reading $PATH in Mac OS X.

Depending on how environment variables are set in Mac OS X, they may not be
recognized in GUI apps [1][2]. This package is needed to pull in user
modifications to PATH, such as giving precedence to binaries from Homebrew
over system binaries with the same name, eg git.

[1]: https://forum.sublimetext.com/t/solved-st2-does-not-respect-system-path-in-osx-10-8/6806  # noqa
[2]: https://stackoverflow.com/a/4567308/149428
"""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import platform
import re
import sys
from os import environ
from subprocess import PIPE, Popen

import sublime
import sublime_plugin

fix_path_settings = None
original_env = {}


def is_mac():
    """This package is only needed on Mac OS X or macOS."""
    return platform.system() == 'Darwin'


def is_sublime_v2():
    """Check if user is running Sublime Text 2.

    ST2 lacks loaded/unloaded handlers, so startup code must be triggered
    manually, first taking care to clean up any messes from last time.
    """
    return int(sublime.version()) < 3000


def get_sys_path():
    """Get the $PATH environment variable from the OS.

    The command to retrieve it is executed using the original environment;
    otherwise, our PATH changes propogate down to the shell we spawn, which
    re-adds the system PATH, resulting in duplication.

    After retrieving the PATH, we decode the byte array into a string, then
    remove ANSI control characters [1], trailing whitespace, and colon.

    [1]: http://www.commandlinefu.com/commands/view/3584/remove-color-codes-special-characters-with-sed  # noqa
    """
    command = ("TERM=ansi CLICOLOR=\"\" SUBLIME=1 "
               "/usr/bin/login -fqpl $USER $SHELL -l -c "
               "'TERM=ansi CLICOLOR=\"\" SUBLIME=1 printf \"%s\" \"$PATH\"'")

    pipe = Popen(command, stdout=PIPE, shell=True, env=original_env)
    sys_path = pipe.stdout.read()

    sys_path_string = sys_path.decode('utf-8')
    ansi_control_chars = re.compile(r'\x1B\[([0-9]{1,2}(;[0-9]{1,2})?)?[m|K]')
    sys_path_string = ansi_control_chars.sub('', sys_path_string)
    sys_path_string = sys_path_string.strip().rstrip(':')
    return sys_path_string


def fix_path():
    """Apply the system PATH to the environment used by Sublime."""
    curr_sys_path = get_sys_path()
    # Basic sanity check to ensure new PATH is not empty
    if len(curr_sys_path) < 1:
        return False

    environ['PATH'] = curr_sys_path

    for pathItem in fix_path_settings.get('additional_path_items', []):
        environ['PATH'] = ':'.join([pathItem, environ['PATH']])

    return True


def plugin_loaded():
    """Setup hooks to reload if settings change and run fix_path().

    Save original environ (particularly PATH) to restore later
    """
    global fix_path_settings, original_env

    fix_path_settings = sublime.load_settings('Preferences.sublime-settings')
    fix_path_settings.clear_on_change('fixpath-reload')
    fix_path_settings.add_on_change('fixpath-reload', fix_path)

    for key in environ:
        original_env[key] = environ[key]

    fix_path()


def plugin_unloaded():
    """Reset PATH to original value.

    This prevents it from becoming duplicated when this plugin is reloaded.
    """
    global fix_path_settings

    environ['PATH'] = original_env['PATH']

    fix_path_settings.clear_on_change('fixpath-reload')


if not is_mac():
    message = ('MacShell will not be loaded because current OS is not Mac '
               'OS X ("Darwin"). Found "{os}".').format(os=platform.system())
    print(message)
    sys.exit()


if is_sublime_v2():
    # Stash the original PATH in the env variable _ST_ORIG_PATH.
    if '_ST_ORIG_PATH' in environ:
        # If _ST_ORIG_PATH exists, restore it as the true path.
        environ['PATH'] = environ['_ST_ORIG_PATH']
    else:
        # If it doesn't exist, create it
        environ['_ST_ORIG_PATH'] = environ['PATH']

    plugin_loaded()
