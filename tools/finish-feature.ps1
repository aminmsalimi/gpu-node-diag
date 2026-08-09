param(
    [Parameter(Mandatory=$true)]
    [string]$Commit,

    [Parameter(Mandatory=$true)]
    [string]$Title,

    [string]$Body = ""
)

$ErrorActionPreference = "Stop"

# ============================================================
# Safety
# ============================================================

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

# ============================================================
# Tests
# ============================================================

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

# ============================================================
# Commit changes if any
# ============================================================

git add -A

$changes = git status --porcelain

if ($changes) {
    Write-Host ""
    Write-Host "Committing changes..." -ForegroundColor Cyan

    git commit -m $Commit

    if ($LASTEXITCODE -ne 0) {
        exit 1
    }
}
else {
    Write-Host "No uncommitted changes."
}

# ============================================================
# Push branch
# ============================================================

Write-Host ""
Write-Host "Pushing $branch..." -ForegroundColor Cyan

git push -u origin $branch

if ($LASTEXITCODE -ne 0) {
    exit 1
}

# ============================================================
# Find existing PR
# ============================================================

Write-Host ""
Write-Host "Checking for existing pull request..." -ForegroundColor Cyan

$prJson = gh pr list `
    --head $branch `
    --base main `
    --state open `
    --json number,url

if ($LASTEXITCODE -ne 0) {
    Write-Host "Unable to query pull requests." -ForegroundColor Red
    exit 1
}

$prList = $prJson | ConvertFrom-Json
$prNumber = $null
$prUrl = $null

if ($prList -and @($prList).Count -gt 0) {
    $prNumber = @($prList)[0].number
    $prUrl = @($prList)[0].url

    Write-Host "Existing PR found: #$prNumber" -ForegroundColor Green
    Write-Host $prUrl
}

# ============================================================
# Create PR if none exists
# ============================================================

if (-not $prNumber) {

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

    $prJson = gh pr view $branch --json number,url

    if ($LASTEXITCODE -ne 0) {
        Write-Host "PR created but could not read PR details." -ForegroundColor Red
        exit 1
    }

    $pr = $prJson | ConvertFrom-Json
    $prNumber = $pr.number
    $prUrl = $pr.url

    Write-Host "Created PR #$prNumber" -ForegroundColor Green
    Write-Host $prUrl
}

# ============================================================
# Wait for GitHub Actions to appear
# ============================================================

Write-Host ""
Write-Host "Waiting for GitHub Actions to register..." -ForegroundColor Cyan

$checksFound = $false

for ($i = 1; $i -le 36; $i++) {

    $statusJson = gh pr view $prNumber --json statusCheckRollup

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Unable to query PR status." -ForegroundColor Red
        exit 1
    }

    $statusData = $statusJson | ConvertFrom-Json

    if ($null -eq $statusData.statusCheckRollup) {
        $checkCount = 0
    }
    else {
        $checkCount = @($statusData.statusCheckRollup).Count
    }

    if ($checkCount -gt 0) {
        $checksFound = $true
        Write-Host "Detected $checkCount CI check(s)." -ForegroundColor Green
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

# ============================================================
# Wait for checks
# ============================================================

Write-Host ""
Write-Host "Waiting for CI to finish..." -ForegroundColor Cyan

gh pr checks $prNumber --watch --fail-fast

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "CI failed." -ForegroundColor Red
    Write-Host "PR left open and was NOT merged."
    Write-Host $prUrl
    exit 1
}

# ============================================================
# Merge
# ============================================================

Write-Host ""
Write-Host "CI passed." -ForegroundColor Green
Write-Host "Merging PR #$prNumber..." -ForegroundColor Cyan

gh pr merge $prNumber --merge

if ($LASTEXITCODE -ne 0) {
    Write-Host "Merge failed. PR remains open." -ForegroundColor Red
    exit 1
}

# ============================================================
# Return to main
# ============================================================

Write-Host ""
Write-Host "Updating local main..." -ForegroundColor Cyan

git checkout main

if ($LASTEXITCODE -ne 0) {
    exit 1
}

git pull --ff-only origin main

if ($LASTEXITCODE -ne 0) {
    exit 1
}

# ============================================================
# Delete finished branches
# ============================================================

$oldPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"

git push origin --delete $branch 2>$null
$remoteDeleteExit = $LASTEXITCODE

git branch -d $branch 2>$null
$localDeleteExit = $LASTEXITCODE

$ErrorActionPreference = $oldPreference

if ($remoteDeleteExit -ne 0) {
    Write-Host "Remote branch was already deleted or could not be removed." -ForegroundColor Yellow
}

if ($localDeleteExit -ne 0) {
    Write-Host "Local feature branch was already deleted or could not be removed." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host " FEATURE FINISHED" -ForegroundColor Green
Write-Host "============================================"
Write-Host "Local tests:       PASSED"
Write-Host "Push:              DONE"
Write-Host "Pull request:      #$prNumber"
Write-Host "GitHub Actions:    PASSED"
Write-Host "Merge:             DONE"
Write-Host "Feature branch:    DELETED"
Write-Host "Local main:        UPDATED"
Write-Host "============================================"