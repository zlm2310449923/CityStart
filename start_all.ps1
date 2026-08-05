$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$services = @(
    @{ Name = 'Residence'; Path = 'residence-service'; Port = 8001 },
    @{ Name = 'Employment'; Path = 'employment-service'; Port = 8002 },
    @{ Name = 'Housing'; Path = 'housing-service'; Port = 8003 },
    @{ Name = 'Matching'; Path = 'service-matching-service'; Port = 8004 },
    @{ Name = 'Gateway'; Path = 'api-gateway'; Port = 8000 }
)

foreach ($service in $services) {
    $servicePath = Join-Path $root $service.Path
    Start-Process powershell -WindowStyle Hidden -WorkingDirectory $servicePath -ArgumentList @(
        '-NoExit', '-Command',
        "`$env:PORT='$($service.Port)'; python -m uvicorn app.main:app --host 0.0.0.0 --port $($service.Port)"
    )
    Write-Host "Started $($service.Name) on port $($service.Port)"
}

$portalPath = Join-Path $root 'citystart-portal'
Start-Process powershell -WindowStyle Hidden -WorkingDirectory $portalPath -ArgumentList @(
    '-NoExit', '-Command', 'python -m http.server 3000'
)
Write-Host 'Started Portal on http://localhost:3000'

