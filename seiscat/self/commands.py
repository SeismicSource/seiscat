# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""Dispatcher for seiscat self command group."""
from __future__ import annotations

from .completion import completion_status, install_completion
from .status import print_self_status
from .update import uninstall_seiscat, update_seiscat


def run_self_command(args):
    """Dispatch `seiscat self ...` commands."""
    if args.self_action == 'status':
        print_self_status()
        return

    if args.self_action == 'logo':
        from ..utils import print_logo
        print_logo(compact=args.compact)
        return

    if args.self_action == 'update':
        print(update_seiscat(git=args.git))
        return

    if args.self_action == 'uninstall':
        print(uninstall_seiscat(yes=args.yes))
        return

    if args.self_action == 'completion':
        if args.self_completion_action == 'status':
            comp = completion_status()
            print(
                'Completion: '
                f"{'installed' if comp['installed'] else 'missing'} "
                f"({comp['shell']}: {comp['details']})"
            )
            return
        if args.self_completion_action == 'install':
            print(install_completion())
            return

    raise ValueError('Unknown self subcommand')
