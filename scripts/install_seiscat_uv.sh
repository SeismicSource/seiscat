#!/usr/bin/env bash
# Copyright (c) 2021-2026 Claudio Satriano <satriano@ipgp.fr>
# SPDX-License-Identifier: GPL-3.0-or-later

set -euo pipefail

DRY_RUN=false

if [ -t 1 ]; then
    C_RESET='\033[0m'
    C_BLUE='\033[1;34m'
    C_GREEN='\033[1;32m'
    C_YELLOW='\033[1;33m'
    C_RED='\033[1;31m'
else
    C_RESET=''
    C_BLUE=''
    C_GREEN=''
    C_YELLOW=''
    C_RED=''
fi

info() {
    printf '%b🐾 [INFO]%b %s\n' "$C_BLUE" "$C_RESET" "$1"
}

ok() {
    printf '%b😺 [OK]%b %s\n' "$C_GREEN" "$C_RESET" "$1"
}

warn() {
    printf '%b⚠️  [WARN]%b %s\n' "$C_YELLOW" "$C_RESET" "$1"
}

fail() {
    printf '%b❌ [ERROR]%b %s\n' "$C_RED" "$C_RESET" "$1" >&2
    exit 1
}

print_banner() {
    printf '%b' "$C_GREEN"
    cat <<'EOF'
   /\_/\
  ( o.o )
   > ^ <   SeiScat
EOF
    printf '%b' "$C_RESET"
}

parse_args() {
    if [ "${1:-}" = '--dry-run' ]; then
        DRY_RUN=true
        shift
    elif [ "${1:-}" = '-h' ] || [ "${1:-}" = '--help' ]; then
        echo 'Usage: scripts/install_seiscat_uv.sh [--dry-run]'
        exit 0
    fi

    if [ $# -ne 0 ]; then
        fail "Unknown argument: $1"
    fi
}

explain_and_confirm() {
    info 'This installer will perform the following actions:'
    info '1) Check if uv is installed and install it if missing.'
    info '2) Install/update seiscat with plotly, cartopy, folium, and pandas via uv tool install.'
    info '3) Install/update argcomplete via uv tool install.'
    info '4) Run activate-global-python-argcomplete and, on zsh, manage a seiscat completion block in ~/.zshrc.'

    if [ "$DRY_RUN" = true ]; then
        warn 'Dry-run mode: commands and file changes will be printed but not executed.'
    fi

    printf 'Do you want to continue? [y/N]: '
    read -r reply
    case "$reply" in
        y|Y|yes|YES)
            ok 'Confirmation received. Proceeding...'
            ;;
        *)
            info 'No problem, installation cancelled. Run the script again anytime.'
            exit 0
            ;;
    esac
}

run_cmd() {
    info "Running: $*"
    if [ "$DRY_RUN" = true ]; then
        warn 'Dry-run mode enabled: command not executed.'
        return 0
    fi
    "$@"
}

activate_argcomplete() {
    local shell_name
    local zsh_marker='# >>> seiscat argcomplete >>>'
    local zsh_end_marker='# <<< seiscat argcomplete <<<'

    shell_name="$(basename "${SHELL:-}")"

    if run_cmd activate-global-python-argcomplete --user; then
        ok 'Legacy global argcomplete activation completed (--user mode).'
    else
        warn 'activate-global-python-argcomplete --user failed.'
        warn 'Retrying without --user (may require elevated permissions)...'
        run_cmd activate-global-python-argcomplete
        ok 'Legacy global argcomplete activation completed.'
    fi

    if [ "$shell_name" = 'zsh' ]; then
        info 'Applying zsh-specific completion snippet for seiscat...'
        if [ "$DRY_RUN" = true ]; then
            warn 'Dry-run mode enabled: ~/.zshrc will not be modified.'
            return 0
        fi
        touch "$HOME/.zshrc"
        if grep -Fq "$zsh_marker" "$HOME/.zshrc"; then
            awk -v start="$zsh_marker" -v end="$zsh_end_marker" '
                $0 == start { in_block = 1; next }
                $0 == end { in_block = 0; next }
                !in_block { print }
            ' "$HOME/.zshrc" > "$HOME/.zshrc.tmp"
            mv "$HOME/.zshrc.tmp" "$HOME/.zshrc"
            info 'Updated existing managed zsh completion snippet in ~/.zshrc.'
        fi

        {
            printf '\n%s\n' "$zsh_marker"
            printf 'autoload -U compinit\n'
            printf 'if ! typeset -f compdef >/dev/null 2>&1; then\n'
            printf '  compinit\n'
            printf 'fi\n'
            printf 'autoload -U +X bashcompinit && bashcompinit\n'
            printf "eval \"\$(register-python-argcomplete seiscat)\"\n"
            printf '%s\n' "$zsh_end_marker"
        } >> "$HOME/.zshrc"
        ok 'Installed zsh completion snippet in ~/.zshrc.'
        info 'Open a new terminal or run: source ~/.zshrc'
    fi
}

install_uv() {
    info 'uv is not installed. Installing uv...'

    if command -v curl >/dev/null 2>&1; then
        info 'Running: curl -LsSf https://astral.sh/uv/install.sh | sh'
        if [ "$DRY_RUN" = false ]; then
            curl -LsSf https://astral.sh/uv/install.sh | sh
        else
            warn 'Dry-run mode enabled: command not executed.'
        fi
    elif command -v wget >/dev/null 2>&1; then
        info 'Running: wget -qO- https://astral.sh/uv/install.sh | sh'
        if [ "$DRY_RUN" = false ]; then
            wget -qO- https://astral.sh/uv/install.sh | sh
        else
            warn 'Dry-run mode enabled: command not executed.'
        fi
    else
        fail 'Neither curl nor wget is available. Install one of them, then re-run this script.'
    fi

    export PATH="$HOME/.local/bin:$PATH"

    if [ "$DRY_RUN" = true ]; then
        ok 'uv installation skipped in dry-run mode.'
        return 0
    fi

    if ! command -v uv >/dev/null 2>&1; then
        fail 'uv installation did not complete successfully. Add ~/.local/bin to PATH and retry.'
    fi

    ok 'uv installed successfully.'
}

main() {
    print_banner
    info 'Starting SeisCat setup with uv for Linux/macOS/WSL...'
    explain_and_confirm

    info 'Step 1/4: Checking if uv is installed...'
    if command -v uv >/dev/null 2>&1; then
        ok "uv is already installed: $(uv --version)"
    else
        install_uv
    fi

    info 'Step 2/4: Installing/updating seiscat with plotly, cartopy, folium, and pandas support...'
    run_cmd uv tool install seiscat --with plotly --with cartopy --with folium --with pandas --upgrade --force
    ok 'seiscat installed/updated with plotly, cartopy, folium, and pandas support.'

    info 'Step 3/4: Installing/updating argcomplete...'
    run_cmd uv tool install argcomplete --upgrade --force
    ok 'argcomplete installed successfully.'

    info 'Step 4/4: Running activate-global-python-argcomplete...'
    activate_argcomplete

    ok 'All done. SeisCat is ready to go.'
    info 'If seiscat is not found in your shell, restart your terminal or ensure ~/.local/bin is in PATH.'
}

parse_args "$@"
main