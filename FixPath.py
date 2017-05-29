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
    command = ("TERM=ansi CLICOLOR=\"\" SUBLIME=1 "
               "/usr/bin/login -fqpl $USER $SHELL -l -c "
               "'TERM=ansi CLICOLOR=\"\" SUBLIME=1 printf \"%s\" \"$PATH\"'")

    # Execute command with original environ. Otherwise, our changes to the PATH
    # propogate down to the shell we spawn, which re-adds the system path &
    # returns it, leading to duplicate values.
    pipe = Popen(command, stdout=PIPE, shell=True, env=original_env)
    sys_path = pipe.stdout.read()

    sys_path_string = sys_path.decode('utf-8')
    # Remove ANSI control characters (see: http://www.commandlinefu.com/commands/view/3584/remove-color-codes-special-characters-with-sed)  # noqa
    ansi_control_chars = re.compile(r'\x1B\[([0-9]{1,2}(;[0-9]{1,2})?)?[m|K]')
    sys_path_string = ansi_control_chars.sub('', sys_path_string)
    # Decode the byte array into a string; remove trailing whitespace, colon
    sys_path_string = sys_path_string.strip().rstrip(':')
    return sys_path_string


def fix_path():
    curr_sys_path = get_sys_path()
    # Basic sanity check to make sure our new path is not empty
    if len(curr_sys_path) < 1:
        return False

    environ['PATH'] = curr_sys_path

    for pathItem in fix_path_settings.get('additional_path_items', []):
        environ['PATH'] = ':'.join([pathItem, environ['PATH']])

    return True


def plugin_loaded():
    global fix_path_settings, original_env

    fix_path_settings = sublime.load_settings('Preferences.sublime-settings')
    fix_path_settings.clear_on_change('fixpath-reload')
    fix_path_settings.add_on_change('fixpath-reload', fix_path)

    # Save the original environ (particularly the original PATH) to restore
    # later
    for key in environ:
        original_env[key] = environ[key]

    fix_path()


def plugin_unloaded():
    global fix_path_settings

    # When we unload, reset PATH to original value. Otherwise, reloads of this
    # plugin will cause the PATH to be duplicated.
    environ['PATH'] = original_env['PATH']

    fix_path_settings.clear_on_change('fixpath-reload')


if not is_mac():
    message = ('FixMacPath will not be loaded because current OS is not Mac '
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
