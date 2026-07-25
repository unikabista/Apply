# run_auto_apply.ps1
# One-click: install deps, then run the auto-apply pipeline

Set-Location $PSScriptRoot

# Install Python dependencies
Write-Host "Installing dependencies..." -ForegroundColor Cyan
pip install -r requirements.txt -q

# Install Playwright browsers (only downloads if not already present)
Write-Host "Ensuring Playwright browsers are installed..." -ForegroundColor Cyan
playwright install chromium

Write-Host "`nStarting auto-apply pipeline...`n" -ForegroundColor Green

# Run the pipeline — interactive mode (asks before each submit)
# To skip all prompts and submit automatically, change to:
#   python auto_apply.py --auto-submit --limit 10
python auto_apply.py --limit 10

Write-Host "`nDone. Check applications-log.csv for results." -ForegroundColor Green
