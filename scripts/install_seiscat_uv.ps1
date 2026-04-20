#!/usr/bin/env pwsh
# Copyright (c) 2021-2026 Claudio Satriano <satriano@ipgp.fr>
# SPDX-License-Identifier: GPL-3.0-or-later

<#
.SYNOPSIS
Install or update SeisCat with uv on Windows.

.DESCRIPTION
This script:
1) Checks if uv is installed and installs it if missing.
2) Installs/updates SeisCat with optional plotting dependencies.
3) Installs/updates argcomplete.
4) Runs activate-global-python-argcomplete.

.PARAMETER DryRun
Print planned commands without executing them.

.PARAMETER Help
Show usage help and exit.

.EXAMPLE
pwsh -NoProfile -File scripts/install_seiscat_uv.ps1

.EXAMPLE
pwsh -NoProfile -File scripts/install_seiscat_uv.ps1 -DryRun

.EXAMPLE
pwsh -NoProfile -File scripts/install_seiscat_uv.ps1 -Help
#>

param(
    [switch]$DryRun,
    [Alias('h')][switch]$Help
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Info {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host "🐾 [INFO] $Message" -ForegroundColor Cyan
}

function Write-Ok {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host "😺 [OK]   $Message" -ForegroundColor Green
}

function Write-WarnMsg {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host "⚠️  [WARN] $Message" -ForegroundColor Yellow
}

function Fail {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host "❌ [ERROR] $Message" -ForegroundColor Red
    exit 1
}

function Show-Banner {
    Write-Host '   /\_/\' -ForegroundColor Green
    Write-Host '  ( o.o )' -ForegroundColor Green
    Write-Host '   > ^ <   SeiScat' -ForegroundColor Green
    Write-Host ''
    Write-Host 'Keep a local seismic catalog' -ForegroundColor Green
    Write-Host 'Copyright (c) 2021-2026 Claudio Satriano' -ForegroundColor Green
    Write-Host ''
}

function Show-Usage {
        @'
Usage:
    pwsh -NoProfile -File scripts/install_seiscat_uv.ps1 [-DryRun] [-Help]

Options:
    -DryRun   Print all steps and commands without executing them.
    -Help     Show this help message and exit.
'@ | Write-Host
}

    function Confirm-Proceed {
        Write-Info "This installer will perform the following actions:"
        Write-Info "1) Check if uv is installed and install it if missing."
        Write-Info "2) Install/update seiscat with plotly, cartopy, folium, and pandas via uv tool install."
        Write-Info "3) Install/update argcomplete via uv tool install."
        Write-Info "4) Run activate-global-python-argcomplete."

        if ($DryRun) {
            Write-WarnMsg "Dry-run mode: commands and file changes will be printed but not executed."
        }

        $reply = Read-Host "Do you want to continue? [y/N]"
        if ($reply -notin @('y', 'Y', 'yes', 'YES')) {
            Write-Info "No problem, installation cancelled. Run the script again anytime."
            exit 0
        }

        Write-Ok "Confirmation received. Proceeding..."
    }

function Test-Command {
    param([Parameter(Mandatory = $true)][string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Invoke-StepCommand {
    param(
        [Parameter(Mandatory = $true)][string]$Display,
        [Parameter(Mandatory = $true)][scriptblock]$ScriptBlock
    )

    Write-Info "Running: $Display"
    if ($DryRun) {
        Write-WarnMsg "Dry-run mode enabled: command not executed."
        return
    }

    & $ScriptBlock
}

function Update-PathForCurrentSession {
    $candidateDirs = @(
        (Join-Path $HOME ".local\\bin"),
        (Join-Path $HOME ".cargo\\bin")
    )

    foreach ($dir in $candidateDirs) {
        if ((Test-Path $dir) -and ($env:PATH -notlike "*$dir*")) {
            $env:PATH = "$dir;$env:PATH"
        }
    }
}

function Install-Uv {
    Write-Info "uv is not installed. Installing uv via official install script..."
    Invoke-StepCommand -Display "Invoke-RestMethod -Uri https://astral.sh/uv/install.ps1 | Invoke-Expression" -ScriptBlock {
        & ([scriptblock]::Create((Invoke-RestMethod -Uri "https://astral.sh/uv/install.ps1")))
    }

    Update-PathForCurrentSession

    if ($DryRun) {
        Write-Ok "uv installation skipped in dry-run mode."
        return
    }

    if (-not (Test-Command "uv")) {
        Fail "uv installation did not complete successfully. Open a new terminal and retry."
    }

    Write-Ok "uv installed successfully: $(uv --version)"
}

function Activate-Argcomplete {
    Write-Info "Step 4/4: Running activate-global-python-argcomplete..."

    $activationCmd = Get-Command "activate-global-python-argcomplete" -ErrorAction SilentlyContinue

    if ($null -ne $activationCmd) {
        try {
            Invoke-StepCommand -Display "activate-global-python-argcomplete --user" -ScriptBlock {
                & $activationCmd.Source --user
            }
            Write-Ok "Global argcomplete activation completed (--user mode)."
        }
        catch {
            Write-WarnMsg "activate-global-python-argcomplete --user failed. Retrying without --user..."
            Invoke-StepCommand -Display "activate-global-python-argcomplete" -ScriptBlock {
                & $activationCmd.Source
            }
            Write-Ok "Global argcomplete activation completed."
        }
        return
    }

    Write-WarnMsg "activate-global-python-argcomplete is not on PATH. Trying via uv tool run..."
    try {
        Invoke-StepCommand -Display "uv tool run --from argcomplete activate-global-python-argcomplete --user" -ScriptBlock {
            uv tool run --from argcomplete activate-global-python-argcomplete --user
        }
        Write-Ok "Global argcomplete activation completed via uv tool run (--user mode)."
    }
    catch {
        Write-WarnMsg "argcomplete activation command failed on this shell."
        Write-WarnMsg "On Windows, this command mainly targets bash-like shells."
        Write-WarnMsg "If you use Git Bash, run activate-global-python-argcomplete there."
    }
}

if ($Help) {
    Show-Usage
    exit 0
}

Show-Banner
Write-Info "Starting SeisCat setup with uv for Windows..."

Confirm-Proceed
if ($DryRun) {
    Write-WarnMsg "Dry-run mode enabled: no commands will be executed and no files will be modified."
}

Write-Info "Step 1/4: Checking if uv is installed..."
if (Test-Command "uv") {
    Write-Ok "uv is already installed: $(uv --version)"
}
else {
    Install-Uv
}

Write-Info "Step 2/4: Installing/updating seiscat with plotly, cartopy, folium, and pandas support..."
Invoke-StepCommand -Display "uv tool install seiscat --with plotly --with cartopy --with folium --with pandas --upgrade --force" -ScriptBlock {
    uv tool install seiscat --with plotly --with cartopy --with folium --with pandas --upgrade --force
}
Write-Ok "seiscat installed/updated with plotly, cartopy, folium, and pandas support."

Write-Info "Step 3/4: Installing/updating argcomplete using uv tool install..."
Invoke-StepCommand -Display "uv tool install argcomplete --upgrade --force" -ScriptBlock {
    uv tool install argcomplete --upgrade --force
}
Write-Ok "argcomplete installed/updated successfully."

Activate-Argcomplete

Write-Ok "All done. SeisCat is ready to go."
Write-Info "If seiscat is not found in this terminal, open a new terminal window and try again."
