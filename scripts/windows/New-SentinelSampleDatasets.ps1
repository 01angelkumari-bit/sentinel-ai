[CmdletBinding()]
param(
    [string]$Destination = [Environment]::GetFolderPath([Environment+SpecialFolder]::Desktop)
)

$ErrorActionPreference = 'Stop'
$datasetDirectory = Join-Path $Destination 'Sentinel AI Sample Datasets'
New-Item -ItemType Directory -Path $datasetDirectory -Force | Out-Null

$regions = @('North', 'South', 'East', 'West', 'Central')
$products = @('Sentinel Core', 'Forecast Studio', 'Risk Monitor', 'Data Fabric', 'Executive Copilot')
$customers = @('Apex Retail', 'Northstar Logistics', 'Cedar Health', 'Orbit Manufacturing', 'Bluewave Services', 'Summit Foods')
$headers = 'Date,Revenue,Orders,Cancelled,Region,Product,Customer'

for ($dataset = 1; $dataset -le 20; $dataset++) {
    $rows = [System.Collections.Generic.List[string]]::new()
    $rows.Add($headers)
    for ($day = 0; $day -lt 75; $day++) {
        $date = (Get-Date '2026-01-01').AddDays(($dataset - 1) * 3 + $day).ToString('yyyy-MM-dd')
        $orders = 18 + (($dataset * 13 + $day * 7) % 94)
        $cancelled = [Math]::Min($orders, (($dataset + $day) % 7))
        $revenue = [Math]::Round(($orders - $cancelled) * (850 + (($dataset * 137 + $day * 31) % 5200)), 2)
        $region = $regions[($dataset + $day) % $regions.Count]
        $product = $products[($dataset * 2 + $day) % $products.Count]
        $customer = $customers[($dataset * 3 + $day) % $customers.Count]
        $rows.Add("$date,$revenue,$orders,$cancelled,$region,$product,$customer")
    }
    $name = '{0:D2}-{1}-business-sales.csv' -f $dataset, $regions[($dataset - 1) % $regions.Count].ToLowerInvariant()
    Set-Content -LiteralPath (Join-Path $datasetDirectory $name) -Value $rows -Encoding utf8
}

Write-Host "Created 20 upload-ready CSV datasets in $datasetDirectory" -ForegroundColor Green
