param(
    [Parameter(Mandatory=$true)]
    [string]$Commit,

    [Parameter(Mandatory=$true)]
    [string]$Title,

    [string]$Body = ""
)

$ErrorActionPreference = "Stop"

$branch = git branch --show-current

if ($branch -eq "main") {
    Write-Host "ERROR: You are on main. Refusing to continue." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Branch: $branch" -ForegroundColor Cyan
Write-Host "Running tests..." -ForegroundColor Cyan

pytest -v

if ($LASTEXITCODE -ne 0) {
    Write-Host "Tests failed. Nothing will be pushed." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Tests passed." -ForegroundColor Green

git add -A

$changes = git status --porcelain

if ($changes) {
    git commit -m $Commit

    if ($LASTEXITCODE -ne 0) {
        exit 1
    }
}
else {
    Write-Host "No uncommitted changes."
}

git push -u origin $branch

if ($LASTEXITCODE -ne 0) {
    exit 1
}

$existingPr = $null

try {
    $existingPr = gh pr view $branch --json url --jq ".url" 2>$null
}
catch {
    $existingPr = $null
}

if (-not $existingPr) {

    if ([string]::IsNullOrWhiteSpace($Body)) {
        $Body = @"
## Summary

Implements $Title.

## Validation

- Full pytest suite
- GitHub Actions CI

All diagnostics remain read-only unless explicitly requested.
"@
    }

    Write-Host ""
    Write-Host "Creating pull request..." -ForegroundColor Cyan

    gh pr create `
        --base main `
        --head $branch `
        --title $Title `
        --body $Body

    if ($LASTEXITCODE -ne 0) {
        exit 1
    }
}
else {
    Write-Host "PR already exists: $existingPr"
}

Write-Host ""
Write-Host "Waiting for GitHub Actions..." -ForegroundColor Cyan

gh pr checks --watch --fail-fast

if ($LASTEXITCODE -ne 0) {
    Write-Host "CI failed. PR will NOT be merged." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "CI passed. Merging PR..." -ForegroundColor Green

gh pr merge `
    --merge `
    --delete-branch

if ($LASTEXITCODE -ne 0) {
    exit 1
}

git checkout main
git pull --ff-only origin main

Write-Host ""
Write-Host "DONE" -ForegroundColor Green
Write-Host "PR merged and local main updated."