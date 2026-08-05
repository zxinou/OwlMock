param(
    [string]$ImageTag = "owlmock:railway-volume-check"
)

$ErrorActionPreference = "Stop"
$runId = [guid]::NewGuid().ToString("N").Substring(0, 12)
$containerName = "owlmock-volume-check-$runId"
$volumeName = "owlmock-volume-check-$runId"

try {
    docker build --tag $ImageTag .
    if ($LASTEXITCODE -ne 0) { throw "Docker image build failed." }

    docker volume create $volumeName | Out-Null
    docker run --rm --entrypoint sh --user root --mount "type=volume,source=$volumeName,target=/data" $ImageTag -c "chown root:root /data && chmod 0755 /data && touch /data/.railway-volume-initialized" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Could not prepare a root-owned mounted volume." }

    docker run --detach --name $containerName --publish "127.0.0.1::8000" --mount "type=volume,source=$volumeName,target=/data" $ImageTag | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Container startup failed." }

    $hostPort = (docker port $containerName 8000/tcp).Trim().Split(":")[-1]
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($hostPort)) {
        throw "Could not determine the container's published health-check port."
    }

    $deadline = (Get-Date).AddSeconds(30)
    while ((Get-Date) -lt $deadline) {
        $running = docker inspect --format '{{.State.Running}}' $containerName
        if ($LASTEXITCODE -ne 0 -or $running -ne "true") {
            docker logs $containerName
            throw "Container stopped before its health endpoint became available."
        }

        try {
            $response = Invoke-WebRequest -Uri "http://127.0.0.1:$hostPort/api/health/live" -TimeoutSec 3
            if ($response.StatusCode -eq 200) {
                Write-Host "Railway-style mounted volume accepted by the live application."
                exit 0
            }
        }
        catch {
            # The container may still be starting; state is checked on the next pass.
        }

        Start-Sleep -Seconds 2
    }

    docker logs $containerName
    throw "Health endpoint did not become available within 30 seconds."
}
finally {
    docker rm --force $containerName 2>$null | Out-Null
    docker volume rm $volumeName 2>$null | Out-Null
}
