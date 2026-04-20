# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""Shell completion helpers for seiscat self commands."""
from __future__ import annotations

import os
from pathlib import Path
import platform
import re
import shutil
import subprocess

ZSH_MARKER = '# >>> seiscat argcomplete >>>'
ZSH_END_MARKER = '# <<< seiscat argcomplete <<<'
BASH_LINE = 'eval "$(register-python-argcomplete seiscat)"'
POWERSHELL_MODULE = 'seiscat-argcomplete.psm1'


def _detect_shell():
    if platform.system().lower().startswith('win'):
        return 'powershell'
    shell = Path(os.environ.get('SHELL', '')).name
    return shell or 'unknown'


def _is_zsh_completion_installed():
    zshrc = Path.home() / '.zshrc'
    if not zshrc.exists():
        return False
    content = zshrc.read_text(encoding='utf-8', errors='ignore')
    if ZSH_MARKER in content:
        return True
    # Also accept manually configured eval lines without SeisCat markers.
    return bool(
        re.search(
            r'register-python-argcomplete\s+seiscat',
            content
        )
    )


def _is_bash_completion_installed():
    bashrc = Path.home() / '.bashrc'
    if not bashrc.exists():
        return False
    return BASH_LINE in bashrc.read_text(encoding='utf-8', errors='ignore')


def _run_capture(command):
    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True
    )
    return completed.stdout.strip()


def _find_powershell_executable():
    return shutil.which('pwsh') or shutil.which('powershell')


def _powershell_module_path():
    return Path.home() / POWERSHELL_MODULE


def _powershell_import_line():
    # Use absolute path to avoid profile cwd-dependent imports.
    return f'Import-Module "{_powershell_module_path()}"'


def _powershell_profile_path():
    ps_exec = _find_powershell_executable()
    if ps_exec is not None:
        try:
            if output := _run_capture([
                ps_exec,
                '-NoProfile',
                '-Command',
                '$PROFILE.CurrentUserAllHosts'
            ]):
                return Path(output)
        except (subprocess.CalledProcessError, OSError):
            pass
    return Path.home() / 'Documents' / 'PowerShell' / 'profile.ps1'


def _is_powershell_completion_installed():
    module_path = _powershell_module_path()
    profile_path = _powershell_profile_path()
    if not module_path.exists() or not profile_path.exists():
        return False
    content = profile_path.read_text(encoding='utf-8', errors='ignore')
    return _powershell_import_line() in content


def completion_status():
    """Return completion status dictionary for current platform/shell."""
    shell = _detect_shell()
    activate_cmd = shutil.which('activate-global-python-argcomplete')
    register_cmd = shutil.which('register-python-argcomplete')

    status = {
        'shell': shell,
        'activate_command_found': bool(activate_cmd),
        'register_command_found': bool(register_cmd),
        'installed': False,
        'details': '',
    }

    if shell == 'zsh':
        status['installed'] = _is_zsh_completion_installed()
        status['details'] = (
            'zsh completion snippet detected'
            if status['installed']
            else 'zsh completion snippet not found'
        )
    elif shell == 'bash':
        status['installed'] = _is_bash_completion_installed()
        status['details'] = (
            'bash completion line detected'
            if status['installed']
            else 'bash completion line not found'
        )
    elif shell == 'powershell':
        status['installed'] = _is_powershell_completion_installed()
        status['details'] = (
            'PowerShell completion module and profile import detected'
            if status['installed']
            else 'PowerShell completion module/profile import not found'
        )
    else:
        status['installed'] = False
        status['details'] = f'unsupported shell: {shell}'

    return status


def _run_command(command):
    subprocess.run(command, check=True)


def _install_powershell_completion():
    module_path = _powershell_module_path()
    profile_path = _powershell_profile_path()
    import_line = _powershell_import_line()

    register_cmd = shutil.which('register-python-argcomplete')
    if register_cmd is not None:
        command = [register_cmd, '--shell', 'powershell', 'seiscat']
    else:
        command = [
            'uv', 'tool', 'run', '--from', 'argcomplete',
            'register-python-argcomplete', '--shell', 'powershell', 'seiscat'
        ]

    shellcode = _run_capture(command)
    module_path.write_text(shellcode + '\n', encoding='utf-8')

    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.touch(exist_ok=True)
    content = profile_path.read_text(encoding='utf-8', errors='ignore')
    if import_line not in content:
        if content and not content.endswith('\n'):
            content += '\n'
        content += import_line + '\n'
        profile_path.write_text(content, encoding='utf-8')

    ps_exec = _find_powershell_executable()
    if ps_exec is not None:
        try:
            _run_command([
                ps_exec,
                '-NoProfile',
                '-Command',
                f'Import-Module "{module_path}" -Force'
            ])
        except subprocess.CalledProcessError:
            # Profile has been updated; module will load in a new shell.
            pass


def _install_zsh_completion():
    zshrc = Path.home() / '.zshrc'
    zshrc.touch(exist_ok=True)
    content = zshrc.read_text(encoding='utf-8', errors='ignore')
    if ZSH_MARKER in content:
        lines = content.splitlines()
        out = []
        in_block = False
        for line in lines:
            if line == ZSH_MARKER:
                in_block = True
                continue
            if line == ZSH_END_MARKER:
                in_block = False
                continue
            if not in_block:
                out.append(line)
        content = '\n'.join(out).rstrip() + '\n'

    snippet = (
        f"\n{ZSH_MARKER}\n"
        'autoload -U compinit\n'
        'if ! typeset -f compdef >/dev/null 2>&1; then\n'
        '  compinit\n'
        'fi\n'
        'autoload -U +X bashcompinit && bashcompinit\n'
        'eval "$(register-python-argcomplete seiscat)"\n'
        f"{ZSH_END_MARKER}\n"
    )
    zshrc.write_text(content + snippet, encoding='utf-8')


def _install_bash_completion():
    bashrc = Path.home() / '.bashrc'
    bashrc.touch(exist_ok=True)
    content = bashrc.read_text(encoding='utf-8', errors='ignore')
    if BASH_LINE not in content:
        if content and not content.endswith('\n'):
            content += '\n'
        content += BASH_LINE + '\n'
        bashrc.write_text(content, encoding='utf-8')


def install_completion():
    """Install shell completion for current shell with best-effort fallback."""
    shell = _detect_shell()
    if activate_cmd := shutil.which('activate-global-python-argcomplete'):
        try:
            _run_command([activate_cmd, '--user'])
        except subprocess.CalledProcessError:
            _run_command([activate_cmd])

    if shell == 'zsh':
        _install_zsh_completion()
        return (
            'Installed zsh completion. '
            'Open a new terminal or run: source ~/.zshrc'
        )
    if shell == 'bash':
        _install_bash_completion()
        return (
            'Installed bash completion. '
            'Open a new terminal or run: source ~/.bashrc'
        )
    if shell == 'powershell':
        _install_powershell_completion()
        return (
            'Installed PowerShell completion. '
            'Open a new terminal (or reload your profile) to apply changes.'
        )
    return f'Completion installation for shell "{shell}" is not supported.'


def uninstall_completion():
    """Remove managed completion snippets/lines."""
    zshrc = Path.home() / '.zshrc'
    if zshrc.exists():
        content = zshrc.read_text(encoding='utf-8', errors='ignore')
        if ZSH_MARKER in content:
            lines = content.splitlines()
            out = []
            in_block = False
            for line in lines:
                if line == ZSH_MARKER:
                    in_block = True
                    continue
                if line == ZSH_END_MARKER:
                    in_block = False
                    continue
                if not in_block:
                    out.append(line)
            zshrc.write_text('\n'.join(out).rstrip() + '\n', encoding='utf-8')

    bashrc = Path.home() / '.bashrc'
    if bashrc.exists():
        lines = bashrc.read_text(
            encoding='utf-8', errors='ignore'
        ).splitlines()
        filtered = [line for line in lines if line.strip() != BASH_LINE]
        bashrc.write_text(
            '\n'.join(filtered).rstrip() + '\n',
            encoding='utf-8'
        )

    ps_profile = _powershell_profile_path()
    import_line = _powershell_import_line()
    if ps_profile.exists():
        lines = ps_profile.read_text(
            encoding='utf-8', errors='ignore'
        ).splitlines()
        filtered = [line for line in lines if line.strip() != import_line]
        ps_profile.write_text(
            '\n'.join(filtered).rstrip() + '\n',
            encoding='utf-8'
        )

    ps_module = _powershell_module_path()
    if ps_module.exists():
        ps_module.unlink()
