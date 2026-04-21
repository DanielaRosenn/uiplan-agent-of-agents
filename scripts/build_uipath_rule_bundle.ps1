<#
.SYNOPSIS
  Assemble the portable UiPath rule bundle and (optionally) sync it into the
  template repo, then produce uipath-rule.zip.

.PARAMETER Destination
  Directory where the bundle tree is staged. Default: extensions/uipath-rule-bundle/staged.

.PARAMETER TemplateRoot
  Optional: path to UiPath_Spec_Project_Template. If provided, the staged
  files are copied on top of it.

.PARAMETER ZipPath
  Optional: where to write uipath-rule.zip. Default: extensions/uipath-rule-bundle/uipath-rule.zip.
#>
param(
  [string]$Destination  = "$PSScriptRoot\..\extensions\uipath-rule-bundle\staged",
  [string]$TemplateRoot = "",
  [string]$ZipPath      = "$PSScriptRoot\..\extensions\uipath-rule-bundle\uipath-rule.zip"
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path "$PSScriptRoot\.."
$Destination = [System.IO.Path]::GetFullPath($Destination)
$ZipPath     = [System.IO.Path]::GetFullPath($ZipPath)

# Source files carried in the bundle. Keep this list in sync with the
# "Layout" section in extensions/uipath-rule-bundle/README.md.
$files = @(
  @{ src = "CLAUDE.md";                             dst = "CLAUDE.md" },
  @{ src = ".cursorrules";                          dst = ".cursorrules" },
  @{ src = ".cursor\rules\uipath.mdc";              dst = ".cursor\rules\uipath.mdc" },
  @{ src = "docs\uipath-cli.md";                    dst = "docs\uipath-cli.md" },
  @{ src = "docs\uipath-cli.verbs.json";            dst = "docs\uipath-cli.verbs.json" },
  @{ src = "docs\uipath-workflows.md";              dst = "docs\uipath-workflows.md" },
  @{ src = "docs\LEARNING_LOOP.md";                 dst = "docs\LEARNING_LOOP.md" },
  @{ src = ".uipath\skills-approved.sha";           dst = ".uipath\skills-approved.sha" },
  @{ src = ".githooks\pre-commit";                  dst = ".githooks\pre-commit" },
  @{ src = ".githooks\pre-push";                    dst = ".githooks\pre-push" },
  @{ src = "scripts\install_git_hooks.ps1";         dst = "scripts\install_git_hooks.ps1" },
  @{ src = "scripts\install_git_hooks.sh";          dst = "scripts\install_git_hooks.sh" },
  @{ src = "extensions\uipath-rule-bundle\README.md"; dst = "README.md" }
)

# Stage --------------------------------------------------------------------
if (Test-Path $Destination) { Remove-Item $Destination -Recurse -Force }
New-Item -ItemType Directory -Path $Destination -Force | Out-Null

foreach ($f in $files) {
  $srcPath = Join-Path $Root $f.src
  $dstPath = Join-Path $Destination $f.dst
  if (-not (Test-Path $srcPath)) {
    throw "Missing bundle source: $srcPath"
  }
  New-Item -ItemType Directory -Path (Split-Path $dstPath -Parent) -Force | Out-Null
  Copy-Item -Path $srcPath -Destination $dstPath -Force
}

Write-Host "Staged bundle at $Destination"

# Sync into template ------------------------------------------------------
if ($TemplateRoot -and (Test-Path $TemplateRoot)) {
  foreach ($f in $files) {
    $dstPath = Join-Path $TemplateRoot $f.dst
    New-Item -ItemType Directory -Path (Split-Path $dstPath -Parent) -Force | Out-Null
    Copy-Item -Path (Join-Path $Destination $f.dst) -Destination $dstPath -Force
  }
  Write-Host "Synced bundle into $TemplateRoot"
}

# Zip ---------------------------------------------------------------------
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Compress-Archive -Path (Join-Path $Destination "*") -DestinationPath $ZipPath -Force
Write-Host "Wrote $ZipPath"
