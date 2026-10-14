@echo off
chcp 65001 >nul
cd /d "%~dp0"
setlocal

set "OUT=project_dump.txt"
set "PSFILE=%TEMP%\dump_wb_project.ps1"

if exist "%OUT%" del "%OUT%"

> "%PSFILE%" echo $ErrorActionPreference = 'SilentlyContinue'
>>"%PSFILE%" echo $exclude = @('venv','.venv','env','__pycache__','.git','node_modules','.idea','.vscode','dist','build','.pytest_cache','.mypy_cache','.ruff_cache','.next','.nuxt','target','obj','.tox','coverage','htmlcov','main_app\web','main_app\static', 'main_app\uploads', 'main_app\_pycache_','main_app\.env','main_app\.env.example')
>>"%PSFILE%" echo $root = (Get-Location).Path
>>"%PSFILE%" echo $out = Join-Path $root 'project_dump.txt'
>>"%PSFILE%" echo $sep = '=' * 80
>>"%PSFILE%" echo $script:count = 0
>>"%PSFILE%" echo $maxSize = 500000
>>"%PSFILE%" echo function Should-Skip($rel) {
>>"%PSFILE%" echo     $candidates = @($rel, ('BuyerScan\' + $rel))
>>"%PSFILE%" echo     foreach ($ex in $exclude) {
>>"%PSFILE%" echo         foreach ($p in $candidates) {
>>"%PSFILE%" echo             if ($p -eq $ex -or $p -like "$ex\*" -or $p -like "*\$ex" -or $p -like "*\$ex\*") { return $true }
>>"%PSFILE%" echo         }
>>"%PSFILE%" echo     }
>>"%PSFILE%" echo     return $false
>>"%PSFILE%" echo }
>>"%PSFILE%" echo function Walk($dir) {
>>"%PSFILE%" echo     foreach ($item in (Get-ChildItem -LiteralPath $dir -Force -ErrorAction SilentlyContinue)) {
>>"%PSFILE%" echo         $rel = $item.FullName.Substring($root.Length + 1)
>>"%PSFILE%" echo         if ($item.Name -eq 'project_dump.txt') { continue }
>>"%PSFILE%" echo         if (-not $item.PSIsContainer -and $item.Extension -eq '.png') { continue }
>>"%PSFILE%" echo         if (Should-Skip $rel) { continue }
>>"%PSFILE%" echo         if ($item.PSIsContainer) { Walk $item.FullName; continue }
>>"%PSFILE%" echo         Add-Content -Path $out -Value $sep
>>"%PSFILE%" echo         Add-Content -Path $out -Value ('FILE: ' + $rel)
>>"%PSFILE%" echo         Add-Content -Path $out -Value ('SIZE: ' + $item.Length + ' bytes')
>>"%PSFILE%" echo         Add-Content -Path $out -Value $sep
>>"%PSFILE%" echo         if ($item.Length -ge $maxSize) {
>>"%PSFILE%" echo             Add-Content -Path $out -Value '[FILE TOO LARGE - CONTENT SKIPPED]'
>>"%PSFILE%" echo         } else {
>>"%PSFILE%" echo             try {
>>"%PSFILE%" echo                 $content = Get-Content -LiteralPath $item.FullName -Raw -ErrorAction Stop
>>"%PSFILE%" echo                 Add-Content -Path $out -Value $content
>>"%PSFILE%" echo             } catch {
>>"%PSFILE%" echo                 Add-Content -Path $out -Value '[BINARY OR UNREADABLE FILE]'
>>"%PSFILE%" echo             }
>>"%PSFILE%" echo         }
>>"%PSFILE%" echo         Add-Content -Path $out -Value ''
>>"%PSFILE%" echo         $script:count++
>>"%PSFILE%" echo     }
>>"%PSFILE%" echo }
>>"%PSFILE%" echo Walk $root
>>"%PSFILE%" echo Write-Host ('Done. Processed files: ' + $script:count)

powershell -NoProfile -ExecutionPolicy Bypass -File "%PSFILE%"
del "%PSFILE%"

echo.
echo Dump saved to: %OUT%
pause