@echo off
chcp 65001 >nul
cd /d "%~dp0"
setlocal

set "OUT=project_dump.txt"
set "PSFILE=%TEMP%\dump_wb_project.ps1"

if exist "%OUT%" del "%OUT%"

> "%PSFILE%" echo $ErrorActionPreference = 'SilentlyContinue'
>>"%PSFILE%" echo $exclude = @('venv','.venv','env','__pycache__','.git','node_modules','.idea','.vscode','dist','build','.pytest_cache','.mypy_cache','.ruff_cache','.next','.nuxt','target','obj','.tox','coverage','htmlcov')
>>"%PSFILE%" echo $root = (Get-Location).Path
>>"%PSFILE%" echo $out = Join-Path $root 'project_dump.txt'
>>"%PSFILE%" echo $sep = '=' * 80
>>"%PSFILE%" echo $count = 0
>>"%PSFILE%" echo $maxSize = 500000
>>"%PSFILE%" echo Get-ChildItem -Path $root -Recurse -File ^| ForEach-Object {
>>"%PSFILE%" echo     $rel = $_.FullName.Substring($root.Length + 1)
>>"%PSFILE%" echo     if ($_.Name -eq 'project_dump.txt') { return }
>>"%PSFILE%" echo     $skip = $false
>>"%PSFILE%" echo     foreach ($ex in $exclude) {
>>"%PSFILE%" echo         if ($rel -like "*\$ex\*" -or $rel -like "$ex\*" -or $rel -like "*\$ex") { $skip = $true; break }
>>"%PSFILE%" echo     }
>>"%PSFILE%" echo     if ($skip) { return }
>>"%PSFILE%" echo     Add-Content -Path $out -Value $sep
>>"%PSFILE%" echo     Add-Content -Path $out -Value ('FILE: ' + $rel)
>>"%PSFILE%" echo     Add-Content -Path $out -Value ('SIZE: ' + $_.Length + ' bytes')
>>"%PSFILE%" echo     Add-Content -Path $out -Value $sep
>>"%PSFILE%" echo     if ($_.Length -ge $maxSize) {
>>"%PSFILE%" echo         Add-Content -Path $out -Value '[FILE TOO LARGE - CONTENT SKIPPED]'
>>"%PSFILE%" echo     } else {
>>"%PSFILE%" echo         try {
>>"%PSFILE%" echo             $content = Get-Content -Path $_.FullName -Raw -ErrorAction Stop
>>"%PSFILE%" echo             Add-Content -Path $out -Value $content
>>"%PSFILE%" echo         } catch {
>>"%PSFILE%" echo             Add-Content -Path $out -Value '[BINARY OR UNREADABLE FILE]'
>>"%PSFILE%" echo         }
>>"%PSFILE%" echo     }
>>"%PSFILE%" echo     Add-Content -Path $out -Value ''
>>"%PSFILE%" echo     $count++
>>"%PSFILE%" echo }
>>"%PSFILE%" echo Write-Host ('Done. Processed files: ' + $count)

powershell -NoProfile -ExecutionPolicy Bypass -File "%PSFILE%"
del "%PSFILE%"

echo.
echo Dump saved to: %OUT%
pause