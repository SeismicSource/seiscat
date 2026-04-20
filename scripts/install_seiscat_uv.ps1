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
4) Registers PowerShell argcomplete integration for seiscat.

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
    Write-Host '~~( ⊙.⊙ )~~ SeisCat' -ForegroundColor Green
    Write-Host 'Keep a local seismic catalog.' -ForegroundColor Green
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
        Write-Info "4) Register PowerShell argcomplete integration for seiscat."

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
    Write-Info "Step 4/4: Registering argcomplete for PowerShell..."

    $profilePath = $PROFILE.CurrentUserAllHosts
    $profileDir = Split-Path -Parent $profilePath
    $modulePath = Join-Path $HOME "seiscat-argcomplete.psm1"
    $importLine = "Import-Module '$modulePath'"

    Write-Info "Generating completion module with register-python-argcomplete..."
    try {
        Invoke-StepCommand -Display "register-python-argcomplete --shell powershell seiscat > $modulePath" -ScriptBlock {
            register-python-argcomplete --shell powershell seiscat | Out-File -FilePath $modulePath -Encoding utf8
        }
        Write-Ok "PowerShell completion module generated: $modulePath"
    }
    catch {
        Write-WarnMsg "register-python-argcomplete is not on PATH. Trying via uv tool run..."
        Invoke-StepCommand -Display "uv tool run --from argcomplete register-python-argcomplete --shell powershell seiscat > $modulePath" -ScriptBlock {
            uv tool run --from argcomplete register-python-argcomplete --shell powershell seiscat | Out-File -FilePath $modulePath -Encoding utf8
        }
        Write-Ok "PowerShell completion module generated via uv tool run: $modulePath"
    }

    if (-not (Test-Path $profileDir)) {
        Invoke-StepCommand -Display "New-Item -ItemType Directory -Path $profileDir -Force" -ScriptBlock {
            New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
        }
    }

    if (-not (Test-Path $profilePath)) {
        Invoke-StepCommand -Display "New-Item -ItemType File -Path $profilePath -Force" -ScriptBlock {
            New-Item -ItemType File -Path $profilePath -Force | Out-Null
        }
    }

    $profileContent = if (Test-Path $profilePath) {
        Get-Content -Path $profilePath -Raw
    }
    else {
        ''
    }

    if ($profileContent -notmatch [regex]::Escape($importLine)) {
        Invoke-StepCommand -Display "Append Import-Module line to $profilePath" -ScriptBlock {
            Add-Content -Path $profilePath -Value "`r`n$importLine"
        }
        Write-Ok "Added argcomplete module import to profile: $profilePath"
    }
    else {
        Write-Info "Profile already imports the argcomplete module."
    }

    Write-Info "Loading completion module in current session..."
    try {
        Invoke-StepCommand -Display "Import-Module '$modulePath'" -ScriptBlock {
            Import-Module $modulePath -Force
        }
        Write-Ok "PowerShell completion is active in this session."
    }
    catch {
        Write-WarnMsg "Could not import completion module in this session."
        Write-WarnMsg "Open a new PowerShell terminal to load profile changes."
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
