from __future__ import absolute_import, division, print_function, unicode_literals

import platform
import re
from os import environ
from subprocess import PIPE, Popen

import sublime
import sublime_plugin


def is_mac():
    return platform.system() == "Darwin"


if is_mac():
    fix_path_settings = None
    original_env = {}

    def get_sys_path():
        command = "TERM=ansi CLICOLOR=\"\" SUBLIME=1 /usr/bin/login -fqpl $USER $SHELL -l -c 'TERM=ansi CLICOLOR=\"\" SUBLIME=1 printf \"%s\" \"$PATH\"'"

        # Execute command with original environ. Otherwise, our changes to the PATH propogate down to
        # the shell we spawn, which re-adds the system path & returns it, leading to duplicate values.
        sys_path = Popen(command, stdout=PIPE, shell=True, env=original_env).stdout.read()

        sys_path_string = sys_path.decode("utf-8")
        # Remove ANSI control characters (see: http://www.commandlinefu.com/commands/view/3584/remove-color-codes-special-characters-with-sed )
        sys_path_string = re.sub(r'\x1B\[([0-9]{1,2}(;[0-9]{1,2})?)?[m|K]', '', sys_path_string)
        sys_path_string = sys_path_string.strip().rstrip(':')

        # Decode the byte array into a string, remove trailing whitespace, remove trailing ':'
        return sys_path_string



    def fix_path():
        curr_sys_path = get_sys_path()
        # Basic sanity check to make sure our new path is not empty
        if len(curr_sys_path) < 1:
            return False

        environ['PATH'] = curr_sys_path

        for pathItem in fix_path_settings.get("additional_path_items", []):
            environ['PATH'] = pathItem + ':' + environ['PATH']

        return True


    def plugin_loaded():
        global fix_path_settings
        fix_path_settings = sublime.load_settings("Preferences.sublime-settings")
        fix_path_settings.clear_on_change('fixpath-reload')
        fix_path_settings.add_on_change('fixpath-reload', fix_path)

        # Save the original environ (particularly the original PATH) to restore later
        global original_env
        for key in environ:
            original_env[key] = environ[key]

        fix_path()


    def plugin_unloaded():
        # When we unload, reset PATH to original value. Otherwise, reloads of this plugin will cause
        # the PATH to be duplicated.
        environ['PATH'] = original_env['PATH']

        global fix_path_settings
        fix_path_settings.clear_on_change('fixpath-reload')


    # Sublime Text 2 doesn't have loaded/unloaded handlers, so trigger startup code manually, first
    # taking care to clean up any messes from last time.
    if int(sublime.version()) < 3000:
        # Stash the original PATH in the env variable _ST_ORIG_PATH.
        if environ.has_key('_ST_ORIG_PATH'):
            # If _ST_ORIG_PATH exists, restore it as the true path.
            environ['PATH'] = environ['_ST_ORIG_PATH']
        else:
            # If it doesn't exist, create it
            environ['_ST_ORIG_PATH'] = environ['PATH']

        plugin_loaded()



else:   # not is_mac()
    print("FixMacPath will not be loaded because current OS is not Mac OS X ('Darwin'). Found '" + platform.system() + "'")
