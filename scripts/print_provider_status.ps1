param(
    [string]$BackendBaseUrl = "http://127.0.0.1:8000"
)

$url = "$($BackendBaseUrl.TrimEnd('/'))/api/system/provider-status"
Write-Host "[print_provider_status] GET $url"

try {
    $response = Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 10
    $response | ConvertTo-Json -Depth 8
} catch {
    Write-Error $_
    exit 1
}
