# -------------------- Run-FullAudit.ps1 (start)
Write-Host "🔍 Starting Full Code Efficiency Audit for APPSIERRA..." -ForegroundColor Cyan
$ErrorActionPreference = "Stop"
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$report = "audit_report_$ts.txt"

# Activate virtual environment
& .\.venv\Scripts\activate

# 1️⃣ Linting & Style (Ruff)
Write-Host "`n[1] Running Ruff..."
ruff check . --statistics | Tee-Object -FilePath $report -Append

# 2️⃣ Typing (Mypy)
Write-Host "`n[2] Running Mypy..."
mypy . | Tee-Object -FilePath $report -Append

# 3️⃣ Dead Code (Vulture)
Write-Host "`n[3] Running Vulture..."
vulture . --min-confidence 90 | Tee-Object -FilePath $report -Append

# 4️⃣ Complexity (Radon)
Write-Host "`n[4] Running Radon..."
radon cc . -a | Tee-Object -FilePath $report -Append

# 5️⃣ Test Coverage
Write-Host "`n[5] Running Tests & Coverage..."
pytest --maxfail=1 --disable-warnings --cov=. --cov-report term-missing | Tee-Object -FilePath $report -Append

# 6️⃣ Mutation Testing
Write-Host "`n[6] Running Mutmut..."
mutmut run | Tee-Object -FilePath $report -Append
mutmut results | Tee-Object -FilePath $report -Append

# 7️⃣ Import Graph
Write-Host "`n[7] Generating Dependency Graph..."
pydeps . --noshow --max-bacon 2 --output=deps_$ts.svg

# 8️⃣ Git Hygiene
Write-Host "`n[8] Checking Git Hygiene..."
git status | Tee-Object -FilePath $report -Append
git diff --stat | Tee-Object -FilePath $report -Append

# 9️⃣ Aggregate Summary
Write-Host "`n✅ Audit completed. Report saved to $report" -ForegroundColor Green
# -------------------- Run-FullAudit.ps1 (end)
