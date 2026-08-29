[CmdletBinding()]
param(
    [switch]$BuildManagerApi,
    [switch]$SkipDocker,
    [switch]$SkipXiaozhi,
    [switch]$ForceRestart,
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = $PSScriptRoot
$ragRoot = Join-Path $repoRoot "rag\SuperMew-main"
$ragFrontendRoot = Join-Path $ragRoot "frontend"
$managerApiRoot = Join-Path $repoRoot "xiaozhi-esp32-server-main\main\manager-api"
$managerWebRoot = Join-Path $repoRoot "xiaozhi-esp32-server-main\main\manager-web"
$xiaozhiRoot = Join-Path $repoRoot "xiaozhi-esp32-server-main\main\xiaozhi-server"
$runtimeRoot = Join-Path $repoRoot "runtime-logs\museum-startup"
$logsRoot = Join-Path $runtimeRoot "logs"
$stateFile = Join-Path $runtimeRoot "state.json"
$redisContainerName = "museum-dev-redis"
$museumManagerApiContainerName = "xiaozhi-museum-manager-api"
$officialManagerWebContainerName = "xiaozhi-esp32-server-web"

function Write-Step {
    param([string]$Message)
    Write-Host "[museum-rag] $Message" -ForegroundColor Cyan
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[museum-rag] $Message" -ForegroundColor Yellow
}

function Ensure-Directory {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Assert-Path {
    param(
        [string]$Path,
        [string]$Message
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        throw $Message
    }
}

function Assert-Command {
    param(
        [string]$Name,
        [string]$Message
    )

    if ($null -eq (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw $Message
    }
}

function Test-Port {
    param(
        [int]$Port,
        [int]$TimeoutMs = 800
    )

    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $async = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne($TimeoutMs, $false)) {
            return $false
        }
        $client.EndConnect($async)
        return $true
    }
    catch {
        return $false
    }
    finally {
        $client.Close()
    }
}

function Get-PortOwnerPid {
    param([int]$Port)

    try {
        $connection = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction Stop | Select-Object -First 1
        if ($null -ne $connection) {
            return [int]$connection.OwningProcess
        }
    }
    catch {
        # Older Windows PowerShell installations may not expose Get-NetTCPConnection.
    }

    foreach ($line in @(& netstat.exe -ano -p tcp 2>$null)) {
        if ($line -match "^\s*TCP\s+\S+:$Port\s+\S+\s+LISTENING\s+(\d+)\s*$") {
            return [int]$Matches[1]
        }
    }

    return 0
}

function Wait-Port {
    param(
        [string]$Name,
        [int]$Port,
        [int]$TimeoutSeconds = 120
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-Port -Port $Port) {
            Write-Step "$Name is listening on 127.0.0.1:$Port"
            return
        }
        Start-Sleep -Seconds 2
    }

    throw "$Name did not start within ${TimeoutSeconds}s. Check logs: $logsRoot"
}

function Invoke-External {
    param(
        [string]$Name,
        [string]$WorkingDirectory,
        [string]$FilePath,
        [string[]]$ArgumentList
    )

    Write-Step "${Name}: $FilePath $($ArgumentList -join ' ')"
    Push-Location $WorkingDirectory
    try {
        & $FilePath @ArgumentList
        if ($LASTEXITCODE -ne 0) {
            throw "$Name failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }
}

function Quote-PowerShellLiteral {
    param([string]$Value)
    return "'" + $Value.Replace("'", "''") + "'"
}

function Start-LoggedService {
    param(
        [string]$Name,
        [int]$Port,
        [string]$WorkingDirectory,
        [string]$Command
    )

    if (Test-Port -Port $Port) {
        $existingPid = Get-PortOwnerPid -Port $Port
        if ($existingPid -gt 0) {
            Write-Warn "$Name already owns 127.0.0.1:$Port (PID=$existingPid); skipping duplicate start."
        }
        else {
            Write-Warn "$Name already owns 127.0.0.1:$Port; skipping duplicate start."
        }
        return [ordered]@{
            pid = $existingPid
            port = $Port
            existing = $true
            cwd = $WorkingDirectory
            command = $Command
            outLog = ""
            errLog = ""
        }
    }

    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $safeName = $Name.ToLowerInvariant().Replace(" ", "-")
    $outLog = Join-Path $logsRoot "$safeName.$stamp.out.log"
    $errLog = Join-Path $logsRoot "$safeName.$stamp.err.log"
    $shell = (Get-Command powershell.exe -ErrorAction Stop).Path
    $cwd = Quote-PowerShellLiteral $WorkingDirectory
    $childCommand = "Set-Location -LiteralPath $cwd; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; " + [char]36 + "env:PYTHONUNBUFFERED = " + [char]39 + "1" + [char]39 + "; " + $Command

    $process = Start-Process `
        -FilePath $shell `
        -ArgumentList @("-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $childCommand) `
        -WorkingDirectory $WorkingDirectory `
        -RedirectStandardOutput $outLog `
        -RedirectStandardError $errLog `
        -WindowStyle Hidden `
        -PassThru

    Write-Step "$Name started, PID=$($process.Id)"
    return [ordered]@{
        pid = $process.Id
        port = $Port
        existing = $false
        cwd = $WorkingDirectory
        command = $Command
        outLog = $outLog
        errLog = $errLog
    }
}

function Stop-ProcessTree {
    param([int]$RootPid)

    if ($RootPid -le 0) {
        return
    }

    # Each service is started through a hidden PowerShell wrapper. Stop its
    # descendants first so Python/Java/Node processes do not survive a restart.
    $children = @(Get-CimInstance -ClassName Win32_Process -Filter "ParentProcessId = $RootPid" -ErrorAction SilentlyContinue)
    foreach ($child in $children) {
        Stop-ProcessTree -RootPid ([int]$child.ProcessId)
    }

    Stop-Process -Id $RootPid -Force -ErrorAction SilentlyContinue
}

function Stop-ProcessFromState {
    param([object]$Service)

    if ($null -eq $Service) {
        return
    }

    $containerName = ""
    try { $containerName = [string]$Service.container } catch { $containerName = "" }
    if (-not [string]::IsNullOrWhiteSpace($containerName)) {
        if (Get-Command docker -ErrorAction SilentlyContinue) {
            & docker rm -f $containerName *> $null
            Write-Step "Stopped previous Docker service $containerName"
        }
        return
    }

    $pidValue = 0
    try { $pidValue = [int]$Service.pid } catch { $pidValue = 0 }
    if ($pidValue -le 0) {
        return
    }

    $process = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
    if ($null -ne $process) {
        Stop-ProcessTree -RootPid $pidValue
        Write-Step "Stopped previous process PID=$pidValue"
    }
}

function Stop-PreviousState {
    if (-not (Test-Path -LiteralPath $stateFile)) {
        return
    }

    try {
        $oldState = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
        foreach ($service in @($oldState.services.PSObject.Properties)) {
            Stop-ProcessFromState -Service $service.Value
        }
    }
    finally {
        Remove-Item -LiteralPath $stateFile -Force -ErrorAction SilentlyContinue
    }
}

function Ensure-DockerReady {
    Assert-Command -Name "docker" -Message "Docker was not found. Install and start Docker Desktop first."

    & docker info *> $null
    if ($LASTEXITCODE -eq 0) {
        return
    }

    $desktop = Join-Path ${env:ProgramFiles} "Docker\Docker\Docker Desktop.exe"
    if (Test-Path -LiteralPath $desktop) {
        Write-Step "Docker Desktop is not ready; attempting to start it."
        Start-Process -FilePath $desktop | Out-Null
    }
    else {
        throw "Docker Desktop is not running. Start it manually and run this script again."
    }

    $deadline = (Get-Date).AddSeconds(120)
    while ((Get-Date) -lt $deadline) {
        & docker info *> $null
        if ($LASTEXITCODE -eq 0) {
            Write-Step "Docker Desktop is ready."
            return
        }
        Start-Sleep -Seconds 3
    }

    throw "Docker Desktop did not become ready within 120s."
}

function Ensure-RagDependencies {
    Ensure-DockerReady
    Push-Location $ragRoot
    try {
        & docker compose up -d
        if ($LASTEXITCODE -ne 0) {
            throw "SuperMew Docker dependencies failed to start."
        }
    }
    finally {
        Pop-Location
    }

    if (-not (Test-Port -Port 6380)) {
        $containers = @(& docker ps -a --format "{{.Names}}")
        if ($containers -contains $redisContainerName) {
            & docker start $redisContainerName | Out-Null
        }
        else {
            & docker run -d --name $redisContainerName -p 6380:6379 redis:7-alpine redis-server --appendonly yes | Out-Null
        }
        if ($LASTEXITCODE -ne 0) {
            throw "The manager-api Redis service on port 6380 failed to start."
        }
    }
}

function Get-DockerContainerEnvironment {
    param([string]$ContainerName)

    $lines = @(& docker inspect $ContainerName --format "{{range .Config.Env}}{{println .}}{{end}}" 2>$null)
    if ($LASTEXITCODE -ne 0 -or $lines.Count -eq 0) {
        return $null
    }

    $values = @{}
    foreach ($line in $lines) {
        $parts = $line -split "=", 2
        if ($parts.Count -eq 2) {
            $values[$parts[0]] = $parts[1]
        }
    }
    return $values
}

function Ensure-OfficialManagerApiContainer {
    param([string]$JarPath)

    if ($null -eq (Get-Command docker -ErrorAction SilentlyContinue)) {
        return $false
    }

    $officialWebExitCode = 1
    $officialWebIdLines = @()
    try {
        $officialWebIdLines = @(& docker inspect $officialManagerWebContainerName --format "{{.Id}}" 2>$null)
        $officialWebExitCode = $LASTEXITCODE
    }
    catch {
        $officialWebIdLines = @()
        $officialWebExitCode = 1
    }
    $officialWebId = if ($officialWebIdLines.Count -gt 0) { [string]$officialWebIdLines[0] } else { "" }
    if ($officialWebExitCode -ne 0 -or [string]::IsNullOrWhiteSpace($officialWebId)) {
        Write-Warn "Official XiaoZhi Docker web container was not found; using the local manager-api configuration."
        return $false
    }

    $officialImage = ([string](@(& docker inspect $officialManagerWebContainerName --format "{{.Config.Image}}" 2>$null)[0])).Trim()
    $officialNetwork = ([string](@(& docker inspect $officialManagerWebContainerName --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}' 2>$null)[0])).Trim()
    $officialEnv = Get-DockerContainerEnvironment -ContainerName $officialManagerWebContainerName
    $dbUrl = if ($officialEnv) { [string]$officialEnv["SPRING_DATASOURCE_DRUID_URL"] } else { "" }
    $dbUser = if ($officialEnv) { [string]$officialEnv["SPRING_DATASOURCE_DRUID_USERNAME"] } else { "" }
    $dbPassword = if ($officialEnv) { [string]$officialEnv["SPRING_DATASOURCE_DRUID_PASSWORD"] } else { "" }
    $redisHost = if ($officialEnv) { [string]$officialEnv["SPRING_DATA_REDIS_HOST"] } else { "" }
    $redisPassword = if ($officialEnv) { [string]$officialEnv["SPRING_DATA_REDIS_PASSWORD"] } else { "" }
    $redisPort = if ($officialEnv) { [string]$officialEnv["SPRING_DATA_REDIS_PORT"] } else { "" }

    if ([string]::IsNullOrWhiteSpace($officialImage) -or
        [string]::IsNullOrWhiteSpace($officialNetwork) -or
        [string]::IsNullOrWhiteSpace($dbUrl) -or
        [string]::IsNullOrWhiteSpace($dbUser) -or
        [string]::IsNullOrWhiteSpace($dbPassword) -or
        [string]::IsNullOrWhiteSpace($redisHost) -or
        [string]::IsNullOrWhiteSpace($redisPort)) {
        Write-Warn "Official Docker database/Redis settings are incomplete; using the local manager-api configuration."
        return $false
    }

    $jarStamp = (Get-Item -LiteralPath $JarPath).LastWriteTimeUtc.Ticks.ToString()
    $existingIdExitCode = 1
    $existingIdLines = @()
    try {
        $existingIdLines = @(& docker inspect $museumManagerApiContainerName --format "{{.Id}}" 2>$null)
        $existingIdExitCode = $LASTEXITCODE
    }
    catch {
        $existingIdLines = @()
        $existingIdExitCode = 1
    }
    $existingId = if ($existingIdLines.Count -gt 0) { [string]$existingIdLines[0] } else { "" }
    $existingRunning = ""
    $existingStamp = ""
    if (-not [string]::IsNullOrWhiteSpace($existingId)) {
        try {
            $existingRunning = ([string](@(& docker inspect $museumManagerApiContainerName --format "{{.State.Running}}" 2>$null)[0])).Trim()
            $existingStamp = ([string](@(& docker inspect $museumManagerApiContainerName --format '{{.Config.Labels.museum_jar_stamp}}' 2>$null)[0])).Trim()
        }
        catch {
            $existingRunning = ""
            $existingStamp = ""
        }
    }
    $needsRecreate = $existingIdExitCode -ne 0 -or [string]::IsNullOrWhiteSpace($existingId) -or
        $existingRunning -ne "true" -or $existingStamp -ne $jarStamp

    if (Test-Port -Port 8003) {
        $publishedNames = @(& docker ps --filter "publish=8003" --format "{{.Names}}" 2>$null)
        $portOwnedByMuseumContainer = $publishedNames -contains $museumManagerApiContainerName
        if (-not $portOwnedByMuseumContainer) {
            Write-Warn "127.0.0.1:8003 is occupied by another process; cannot replace it with the official-data manager-api."
            return $false
        }
    }

    if ($needsRecreate -and -not [string]::IsNullOrWhiteSpace($existingId)) {
        & docker rm -f $museumManagerApiContainerName *> $null
    }

    if ($needsRecreate) {
        $dockerArgs = @(
            "run", "-d",
            "--name", $museumManagerApiContainerName,
            "--restart", "unless-stopped",
            "--network", $officialNetwork,
            "--add-host", "host.docker.internal:host-gateway",
            "-p", "8003:8003",
            "--label", "museum_jar_stamp=$jarStamp",
            "-v", "$JarPath`:/app/museum-api.jar:ro",
            "--entrypoint", "java",
            $officialImage,
            "-Xms256m", "-Xmx768m",
            "-jar", "/app/museum-api.jar",
            "--spring.profiles.active=dev",
            "--server.port=8003",
            "--spring.datasource.druid.url=$dbUrl",
            "--spring.datasource.druid.username=$dbUser",
            "--spring.datasource.druid.password=$dbPassword",
            "--spring.data.redis.host=$redisHost",
            "--spring.data.redis.password=$redisPassword",
            "--spring.data.redis.port=$redisPort",
            "--museum-rag.base-url=http://host.docker.internal:8000",
            "--museum-rag.workbench-url=http://127.0.0.1:8000"
        )
        & docker @dockerArgs *> $null
        if ($LASTEXITCODE -ne 0) {
            throw "The official-data manager-api Docker service failed to start."
        }
        Write-Step "manager-api is using the official XiaoZhi database and Redis."
    }
    else {
        Write-Step "manager-api Docker service is already using the current source JAR."
    }

    return $true
}

function Resolve-VenvPython {
    param(
        [string]$Root,
        [string[]]$VenvNames
    )

    foreach ($name in $VenvNames) {
        $candidate = Join-Path $Root "$name\Scripts\python.exe"
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    throw "No usable Python virtual environment was found under $Root."
}

Ensure-Directory -Path $runtimeRoot
Ensure-Directory -Path $logsRoot

Assert-Path -Path $ragRoot -Message "RAG project directory was not found: $ragRoot"
Assert-Path -Path $managerApiRoot -Message "manager-api directory was not found: $managerApiRoot"
Assert-Path -Path $managerWebRoot -Message "manager-web directory was not found: $managerWebRoot"
Assert-Path -Path $xiaozhiRoot -Message "xiaozhi-server directory was not found: $xiaozhiRoot"

Assert-Command -Name "npm.cmd" -Message "npm was not found. Install Node.js first."
Assert-Command -Name "java.exe" -Message "Java was not found. Install JDK 21 first."

$ragPython = Resolve-VenvPython -Root $ragRoot -VenvNames @(".agent-venv", ".venv")
$xiaozhiPython = Resolve-VenvPython -Root $xiaozhiRoot -VenvNames @(".agent-venv-xiaozhi", ".agent-venv", ".venv")
$javaPath = (Get-Command java.exe -ErrorAction Stop).Path
$npmPath = (Get-Command npm.cmd -ErrorAction Stop).Path

if ($ForceRestart) {
    Write-Step "ForceRestart is enabled; stopping services recorded by the previous run."
    Stop-PreviousState
}

if (-not $SkipDocker) {
    Ensure-RagDependencies
}
else {
    Write-Warn "Docker startup was skipped. Ensure PostgreSQL, Redis and Milvus are already running."
}

$ragIndex = Join-Path $ragFrontendRoot "dist\index.html"
if (-not (Test-Path -LiteralPath $ragIndex)) {
    Invoke-External -Name "Build SuperMew frontend" -WorkingDirectory $ragFrontendRoot -FilePath $npmPath -ArgumentList @("run", "build")
}

$managerJar = Join-Path $managerApiRoot "target\xiaozhi-esp32-api.jar"
$managerBuildInputs = @(
    Get-ChildItem -LiteralPath (Join-Path $managerApiRoot "src") -Recurse -File -ErrorAction Stop
    Get-Item -LiteralPath (Join-Path $managerApiRoot "pom.xml") -ErrorAction Stop
)
$latestManagerInput = $managerBuildInputs | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$managerJarNeedsBuild = -not (Test-Path -LiteralPath $managerJar)
if (-not $managerJarNeedsBuild) {
    $managerJarItem = Get-Item -LiteralPath $managerJar
    $managerJarNeedsBuild = $latestManagerInput.LastWriteTime -gt $managerJarItem.LastWriteTime
}

if ($BuildManagerApi -or $managerJarNeedsBuild) {
    Assert-Command -Name "mvn" -Message "manager-api must be rebuilt, but Maven was not found. Install Maven first."
    if ($managerJarNeedsBuild) {
        Write-Step "manager-api source is newer than the jar; rebuilding it."
    }
    Invoke-External -Name "Build manager-api" -WorkingDirectory $managerApiRoot -FilePath "mvn" -ArgumentList @("-DskipTests", "package")
}
Assert-Path -Path $managerJar -Message "manager-api jar was not found: $managerJar"

$opus = Get-ChildItem -LiteralPath (Join-Path $xiaozhiRoot "tmp\opus-lib") -Recurse -File -Filter "opus.dll" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -eq $opus -and -not $SkipXiaozhi) {
    throw "opus.dll was not found. Put the Opus library under xiaozhi-server\tmp\opus-lib."
}

$ragCommand = "& $(Quote-PowerShellLiteral $ragPython) -m uvicorn backend.app:app --host 0.0.0.0 --port 8000"
$managerApiCommand = "& $(Quote-PowerShellLiteral $javaPath) -Xms256m -Xmx768m -jar $(Quote-PowerShellLiteral $managerJar) --spring.profiles.active=dev --server.port=8003 --spring.data.redis.port=6380"
$managerApiUsesOfficialData = Ensure-OfficialManagerApiContainer -JarPath $managerJar
$managerWebCommand = '$env:VUE_APP_API_PROXY_TARGET = ' + (Quote-PowerShellLiteral "http://127.0.0.1:8003") + "; & " + (Quote-PowerShellLiteral $npmPath) + " run serve -- --host 0.0.0.0 --port 8001"

$state = [ordered]@{
    generatedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    repoRoot = $repoRoot
    urls = [ordered]@{
        managerWeb = "http://127.0.0.1:8001/"
        managerApi = "http://127.0.0.1:8003/xiaozhi"
        ragWorkbench = "http://127.0.0.1:8000/"
        xiaozhiWebsocket = "ws://127.0.0.1:8011/xiaozhi/v1/"
        xiaozhiOta = "http://127.0.0.1:8013/xiaozhi/ota/"
    }
    services = [ordered]@{}
}

$state.services.rag = Start-LoggedService -Name "rag-api" -Port 8000 -WorkingDirectory $ragRoot -Command $ragCommand
$state.services.managerApi = if ($managerApiUsesOfficialData) {
    [ordered]@{
        container = $museumManagerApiContainerName
        port = 8003
        existing = $true
        cwd = $managerApiRoot
        command = "docker container $museumManagerApiContainerName"
        outLog = ""
        errLog = ""
    }
}
else {
    Start-LoggedService -Name "manager-api" -Port 8003 -WorkingDirectory $managerApiRoot -Command $managerApiCommand
}
$state.services.managerWeb = Start-LoggedService -Name "manager-web" -Port 8001 -WorkingDirectory $managerWebRoot -Command $managerWebCommand

if ($SkipXiaozhi) {
    Write-Warn "xiaozhi-server startup was skipped."
    $state.services.xiaozhi = [ordered]@{ skipped = $true; port = 8011 }
}
else {
    $opusDirectory = $opus.Directory.FullName
    $xiaozhiCommand = '$env:PATH = ' + (Quote-PowerShellLiteral ($opusDirectory + ';')) + ' + $env:PATH; & ' + (Quote-PowerShellLiteral $xiaozhiPython) + ' -u app.py'
    $state.services.xiaozhi = Start-LoggedService -Name "xiaozhi-server" -Port 8011 -WorkingDirectory $xiaozhiRoot -Command $xiaozhiCommand
}

$state | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $stateFile -Encoding UTF8

Wait-Port -Name "RAG API" -Port 8000 -TimeoutSeconds 120
Wait-Port -Name "manager-api" -Port 8003 -TimeoutSeconds 180
Wait-Port -Name "manager-web" -Port 8001 -TimeoutSeconds 90
if (-not $SkipXiaozhi) {
    Wait-Port -Name "xiaozhi WebSocket" -Port 8011 -TimeoutSeconds 120
    Wait-Port -Name "xiaozhi HTTP" -Port 8013 -TimeoutSeconds 120
}

Write-Host ""
Write-Host "Museum RAG local services are ready." -ForegroundColor Green
Write-Host "Daily entry (one manager login): $($state.urls.managerWeb)" -ForegroundColor Green
Write-Host "RAG advanced workbench: $($state.urls.ragWorkbench)" -ForegroundColor DarkGray
Write-Host "Log directory: $logsRoot" -ForegroundColor Yellow
Write-Host ""

if ($OpenBrowser) {
    Start-Process $state.urls.managerWeb | Out-Null
}
