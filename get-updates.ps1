param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$BranchName
)

# Color output functions
function Write-Header($text) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host $text -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Success($text) {
    Write-Host $text -ForegroundColor Green
}

function Write-Info($text) {
    Write-Host $text -ForegroundColor Yellow
}

# Fetch the branch
Write-Header "Fetching branch: $BranchName"
try {
    git fetch origin $BranchName 2>&1 | Write-Host
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to fetch branch. Please check the branch name." -ForegroundColor Red
        exit 1
    }
    Write-Success "Branch fetched successfully"
} catch {
    Write-Host "Error fetching branch: $_" -ForegroundColor Red
    exit 1
}

# Show commit log
Write-Header "Commits in $BranchName (not in current branch)"
git log HEAD..FETCH_HEAD --oneline --decorate --color=always
if ($LASTEXITCODE -ne 0) {
    Write-Info "No new commits or unable to compare"
}

# Show files changed
Write-Header "Files Changed"
git diff --name-status HEAD..FETCH_HEAD
if ($LASTEXITCODE -ne 0) {
    Write-Info "No file changes or unable to compare"
}

# Show statistics
Write-Header "Change Statistics"
git diff --stat HEAD..FETCH_HEAD
if ($LASTEXITCODE -ne 0) {
    Write-Info "No statistics available"
}

# Ask if user wants to see full diff
Write-Host ""
$response = Read-Host "Would you like to see the full diff? (y/n)"
if ($response -eq 'y' -or $response -eq 'Y') {
    Write-Header "Full Diff"
    git diff HEAD..FETCH_HEAD
}

# Summary
Write-Header "Summary"
$commitCount = git rev-list --count HEAD..FETCH_HEAD 2>$null
if ($LASTEXITCODE -eq 0 -and $commitCount) {
    Write-Success "Total commits: $commitCount"
} else {
    Write-Info "Unable to count commits"
}

Write-Host ""
Write-Host "To merge these changes into your current branch, run:" -ForegroundColor Yellow
Write-Host "  git merge origin/$BranchName" -ForegroundColor White
Write-Host ""
Write-Host "To checkout this branch, run:" -ForegroundColor Yellow
Write-Host "  git checkout $BranchName" -ForegroundColor White
Write-Host ""
