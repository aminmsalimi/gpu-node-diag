param(
    [Parameter(Mandatory=$true)]
    [string]$Commit,

    [Parameter(Mandatory=$true)]
    [string]$Title,

    [string]$Body = ""
)

$ErrorActionPreference = "Stop"

# --------------------------------------------------
# Safety
# --------------------------------------------------

$branch = (git branch --show-current).Trim()

if (-not $branch) {
    Write-Host "ERROR: Could not determine current branch." -ForegroundColor Red
    exit 1
}

if ($branch -eq "main") {
    Write-Host "ERROR: You are on main. Refusing to continue." -ForegroundColor Red
    exit 1
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: GitHub CLI (gh) is not available." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Branch: $branch" -ForegroundColor Cyan

# --------------------------------------------------
# Local tests
# --------------------------------------------------

Write-Host ""
Write-Host "Running tests..." -ForegroundColor Cyan

pytest -v

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Tests failed. Nothing will be pushed." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Tests passed." -ForegroundColor Green

# --------------------------------------------------
# Commit
# --------------------------------------------------

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

# --------------------------------------------------
# Push
# --------------------------------------------------

Write-Host ""
Write-Host "Pushing $branch..." -ForegroundColor Cyan

git push -u origin $branch

if ($LASTEXITCODE -ne 0) {
    exit 1
}

# --------------------------------------------------
# Find or create PR
# --------------------------------------------------

$prUrl = gh pr list `
    --head $branch `
    --base main `
    --state open `
    --json url `
    --jq '.[0].url // ""'

if ($LASTEXITCODE -ne 0) {
    Write-Host "Unable to query pull requests." -ForegroundColor Red
    exit 1
}

if ([string]::IsNullOrWhiteSpace($prUrl)) {

    if ([string]::IsNullOrWhiteSpace($Body)) {
        $Body = @"
## Summary

$Title

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

    $prUrl = gh pr view $branch --json url --jq '.url'
}
else {
    Write-Host ""
    Write-Host "Existing PR: $prUrl" -ForegroundColor Cyan
}

# --------------------------------------------------
# Wait for GitHub Actions to register
# --------------------------------------------------

Write-Host ""
Write-Host "Waiting for GitHub Actions..." -ForegroundColor Cyan

$checksFound = $false

for ($i = 1; $i -le 36; $i++) {

    $checkCount = gh pr view $branch `
        --json statusCheckRollup `
        --jq '.statusCheckRollup | length'

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Unable to query PR checks." -ForegroundColor Red
        exit 1
    }

    $count = 0
    [int]::TryParse(
        $checkCount.ToString().Trim(),
        [ref]$count
    ) | Out-Null

    if ($count -gt 0) {
        $checksFound = $true
        break
    }

    Write-Host "CI not registered yet... waiting 5 seconds ($i/36)"
    Start-Sleep -Seconds 5
}

if (-not $checksFound) {
    Write-Host ""
    Write-Host "No CI checks appeared after 3 minutes." -ForegroundColor Red
    Write-Host "PR left open. Nothing was merged."
    Write-Host $prUrl
    exit 1
}

# --------------------------------------------------
# Watch CI
# --------------------------------------------------

Write-Host ""
Write-Host "CI detected. Waiting for completion..." -ForegroundColor Cyan

$oldPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"

gh pr checks $branch --watch --fail-fast

$ciExitCode = $LASTEXITCODE
$ErrorActionPreference = $oldPreference

if ($ciExitCode -ne 0) {
    Write-Host ""
    Write-Host "CI failed. PR left open and was NOT merged." -ForegroundColor Red
    Write-Host $prUrl
    exit 1
}

# --------------------------------------------------
# Merge
# --------------------------------------------------

Write-Host ""
Write-Host "CI passed." -ForegroundColor Green
Write-Host "Merging PR..." -ForegroundColor Cyan

gh pr merge $branch `
    --merge `
    --delete-branch

if ($LASTEXITCODE -ne 0) {
    Write-Host "Merge failed. PR remains open." -ForegroundColor Red
    exit 1
}

# --------------------------------------------------
# Sync main
# --------------------------------------------------

git checkout main

if ($LASTEXITCODE -ne 0) {
    exit 1
}

git pull --ff-only origin main

if ($LASTEXITCODE -ne 0) {
    exit 1
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "DONE" -ForegroundColor Green
Write-Host "============================================"
Write-Host "Local tests:       PASSED"
Write-Host "Push:              DONE"
Write-Host "Pull request:      DONE"
Write-Host "GitHub Actions:    PASSED"
Write-Host "Merge:             DONE"
Write-Host "Remote branch:     DELETED"
Write-Host "Local main:        UPDATED"
Write-Host "============================================"