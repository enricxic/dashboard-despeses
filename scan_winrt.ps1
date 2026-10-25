param(
    [Parameter(Mandatory=$true)]
    [string]$OutputDir
)

$ErrorActionPreference = 'Stop'

try {
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    
    $asTaskGeneric1 = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { 
        $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' 
    }
    $asTaskGeneric2 = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { 
        $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperationWithProgress`2' 
    }

    function AwaitOp($WinRtTask, $ResultType) {
        $asTask = $asTaskGeneric1.MakeGenericMethod($ResultType)
        $netTask = $asTask.Invoke($null, @($WinRtTask))
        $netTask.Wait(-1) | Out-Null
        $netTask.Result
    }

    function AwaitProg($WinRtTask, $ResultType, $ProgressType) {
        $asTask = $asTaskGeneric2.MakeGenericMethod($ResultType, $ProgressType)
        $netTask = $asTask.Invoke($null, @($WinRtTask))
        $netTask.Wait(-1) | Out-Null
        $netTask.Result
    }

    [Windows.Devices.Enumeration.DeviceInformation, Windows.Devices.Enumeration, ContentType = WindowsRuntime] | Out-Null
    [Windows.Devices.Scanners.ImageScanner, Windows.Devices.Scanners, ContentType = WindowsRuntime] | Out-Null
    [Windows.Devices.Scanners.ImageScannerScanResult, Windows.Devices.Scanners, ContentType = WindowsRuntime] | Out-Null
    [Windows.Storage.StorageFolder, Windows.Storage, ContentType = WindowsRuntime] | Out-Null

    if (-not (Test-Path $OutputDir)) {
        New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    }

    $storageFolder = AwaitOp ([Windows.Storage.StorageFolder]::GetFolderFromPathAsync($OutputDir)) ([Windows.Storage.StorageFolder])

    $selector = [Windows.Devices.Scanners.ImageScanner]::GetDeviceSelector()
    $devices = AwaitOp ([Windows.Devices.Enumeration.DeviceInformation]::FindAllAsync($selector)) ([Windows.Devices.Enumeration.DeviceInformationCollection])

    if ($devices.Count -eq 0) {
        Write-Output "ERROR:No s'ha trobat cap escàner connectat."
        exit 1
    }

    $scanner = AwaitOp ([Windows.Devices.Scanners.ImageScanner]::FromIdAsync($devices[0].Id)) ([Windows.Devices.Scanners.ImageScanner])

    # Scan from Flatbed if supported, else Default
    $source = if ($scanner.IsScanSourceSupported([Windows.Devices.Scanners.ImageScannerScanSource]::Flatbed)) {
        [Windows.Devices.Scanners.ImageScannerScanSource]::Flatbed
    } else {
        [Windows.Devices.Scanners.ImageScannerScanSource]::Default
    }

    $scanOp = $scanner.ScanFilesToFolderAsync($source, $storageFolder)
    $scanResult = AwaitProg $scanOp ([Windows.Devices.Scanners.ImageScannerScanResult]) ([System.UInt32])

    if ($scanResult.ScannedFiles.Count -gt 0) {
        $file = $scanResult.ScannedFiles[0]
        Write-Output "SUCCESS:$($file.Path)"
    } else {
        Write-Output "ERROR:L'escàner no ha retornat cap fitxer."
        exit 1
    }
} catch {
    Write-Output "ERROR:$($_.Exception.Message)"
    exit 1
}
