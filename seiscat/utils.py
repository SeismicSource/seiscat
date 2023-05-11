# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Utility functions for seiscat.

:copyright:
    2022-2023 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import os
import sys
from .configobj import ConfigObj
from .configobj.validate import Validator


def err_exit(msg):
    msg = str(msg)
    sys.stderr.write(msg + '\n')
    sys.exit(1)


def parse_configspec():
    curdir = os.path.dirname(__file__)
    configspec_file = os.path.join(curdir, 'conf', 'configspec.conf')
    return read_config(configspec_file)


def write_ok(filepath):
    if os.path.exists(filepath):
        ans = input(
            f'"{filepath}" already exists. Do you want to overwrite it? [y/N] '
        )
        return ans in ['y', 'Y']
    return True


def write_sample_config(configspec, progname):
    c = ConfigObj(configspec=configspec, default_encoding='utf8')
    val = Validator()
    c.validate(val)
    c.defaults = []
    c.initial_comment = configspec.initial_comment
    c.comments = configspec.comments
    c.final_comment = configspec.final_comment
    configfile = f'{progname}.conf'
    if write_ok(configfile):
        with open(configfile, 'wb') as fp:
            c.write(fp)
        print(f'Sample config file written to: "{configfile}"')


def read_config(config_file, configspec=None):
    kwargs = dict(
        configspec=configspec, file_error=True, default_encoding='utf8')
    if configspec is None:
        kwargs.update(
            dict(interpolation=False, list_values=False, _inspec=True))
    try:
        config_obj = ConfigObj(config_file, **kwargs)
    except IOError as err:
        err_exit(err)
    except Exception as err:
        msg = f'Unable to read "{config_file}": {err}'
        err_exit(msg)
    for k, v in config_obj.items():
        if v == 'None':
            config_obj[k] = None
    return config_obj


def validate_config(config_obj):
    val = Validator()
    test = config_obj.validate(val)
    if isinstance(test, dict):
        for entry in test:
            if not test[entry]:
                sys.stderr.write(
                    f'Invalid value for "{entry}": "{config_obj[entry]}"\n')
        sys.exit(1)
    if not test:
        err_exit('No configuration value present!')
