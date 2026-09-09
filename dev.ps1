# Starts the FastAPI backend (8010) and Vite frontend (5173) on Windows.
# Ctrl+C, an error, or normal script exit stops both process trees.

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

function Stop-ProcessTree {
    param([System.Diagnostics.Process]$Process)

    if ($null -eq $Process) {
        return
    }
    try {
        $Process.Refresh()
        if (-not $Process.HasExited) {
            & taskkill.exe /PID $Process.Id /T /F 2>$null | Out-Null
        }
    } catch {
        # The process may already have exited while shutdown is in progress.
    }
}

if (-not (Test-Path ".env" -PathType Leaf)) {
    throw "未找到 .env。请先运行：Copy-Item .env.example .env，并填写 RESUME_AGENT_API_KEY。"
}

if (-not (Test-Path "agent/frontend/node_modules" -PathType Container)) {
    throw "未安装前端依赖。请先运行：pnpm --dir agent/frontend install"
}

foreach ($command in @("uv", "pnpm")) {
    if ($null -eq (Get-Command $command -ErrorAction SilentlyContinue)) {
        throw "未找到 $command。请安装后重新运行此脚本。"
    }
}

$backend = $null
$frontend = $null
try {
    $backend = Start-Process -FilePath "uv" -ArgumentList @(
        "run", "uvicorn", "resume_agent.api.main:app", "--app-dir", "agent/src",
        "--host", "127.0.0.1", "--port", "8010", "--reload", "--reload-dir", "agent/src"
    ) -PassThru -NoNewWindow

    $backendReady = $false
    for ($attempt = 0; $attempt -lt 120; $attempt++) {
        try {
            Invoke-WebRequest -Uri "http://127.0.0.1:8010/" -UseBasicParsing -TimeoutSec 1 | Out-Null
            $backendReady = $true
            break
        } catch {
            Start-Sleep -Milliseconds 250
            $backend.Refresh()
            if ($backend.HasExited) {
                throw "后端进程已退出，退出代码：$($backend.ExitCode)"
            }
        }
    }
    if (-not $backendReady) {
        throw "后端未能在 30 秒内就绪，请检查启动日志。"
    }

    $frontend = Start-Process -FilePath "pnpm.cmd" -ArgumentList @(
        "--dir", "agent/frontend", "dev"
    ) -PassThru -NoNewWindow

    Write-Host ""
    Write-Host "────────────────────────────────────────────────"
    Write-Host "  Resume Generator 已启动"
    Write-Host ""
    Write-Host "  前端工作台  http://localhost:5173"
    Write-Host "  后端 API    http://127.0.0.1:8010"
    Write-Host "  API 文档    http://127.0.0.1:8010/docs"
    Write-Host ""
    Write-Host "  请在浏览器中打开前端工作台开始使用。"
    Write-Host "  按 Ctrl+C 可安全停止前端、后端及其子进程。"
    Write-Host "────────────────────────────────────────────────"
    Write-Host ""

    while (-not $backend.HasExited -and -not $frontend.HasExited) {
        Start-Sleep -Seconds 1
        $backend.Refresh()
        $frontend.Refresh()
    }

    if ($backend.HasExited) {
        throw "后端进程已退出，退出代码：$($backend.ExitCode)"
    }
    throw "前端进程已退出，退出代码：$($frontend.ExitCode)"
} finally {
    Write-Host ""
    Write-Host "正在关闭前端、后端及其子进程…"
    Stop-ProcessTree $frontend
    Stop-ProcessTree $backend
}
