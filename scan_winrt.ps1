param(
    [string]$OutputDir = "",
    [string]$DeviceName = "",
    [int]$Dpi = 300,
    [string]$ColorMode = "Color",
    [switch]$ListDevices
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

    $selector = [Windows.Devices.Scanners.ImageScanner]::GetDeviceSelector()
    $devices = AwaitOp ([Windows.Devices.Enumeration.DeviceInformation]::FindAllAsync($selector)) ([Windows.Devices.Enumeration.DeviceInformationCollection])

    if ($ListDevices) {
        if ($devices.Count -eq 0) {
            Write-Output "NO_DEVICES"
        } else {
            foreach ($d in $devices) {
                Write-Output "DEVICE:$($d.Name)|$($d.Id)"
            }
        }
        exit 0
    }

    if ($devices.Count -eq 0) {
        Write-Output "ERROR:No s'ha trobat cap escàner connectat."
        exit 1
    }

    # Seleccionar escàner per nom si s'ha especificat, o el primer disponible
    $selectedDevice = $devices[0]
    if ($DeviceName -and $DeviceName -ne "default" -and $DeviceName -ne "") {
        foreach ($d in $devices) {
            if ($d.Name -like "*$DeviceName*" -or $d.Id -like "*$DeviceName*") {
                $selectedDevice = $d
                break
            }
        }
    }

    if (-not $OutputDir) {
        Write-Output "ERROR:Cal indicar el paràmetre -OutputDir per desar la imatge."
        exit 1
    }

    if (-not (Test-Path $OutputDir)) {
        New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    }

    $storageFolder = AwaitOp ([Windows.Storage.StorageFolder]::GetFolderFromPathAsync($OutputDir)) ([Windows.Storage.StorageFolder])
    $scanner = AwaitOp ([Windows.Devices.Scanners.ImageScanner]::FromIdAsync($selectedDevice.Id)) ([Windows.Devices.Scanners.ImageScanner])

    # Scan from Flatbed if supported, else Default
    $source = if ($scanner.IsScanSourceSupported([Windows.Devices.Scanners.ImageScannerScanSource]::Flatbed)) {
        [Windows.Devices.Scanners.ImageScannerScanSource]::Flatbed
    } else {
        [Windows.Devices.Scanners.ImageScannerScanSource]::Default
    }

    # Configuració opcional de color/mode si s'utilitza Flatbed
    if ($source -eq [Windows.Devices.Scanners.ImageScannerScanSource]::Flatbed) {
        try {
            $flatbed = $scanner.FlatbedConfiguration
            if ($ColorMode -eq "Grayscale" -or $ColorMode -eq "Grisos") {
                $flatbed.ColorMode = [Windows.Devices.Scanners.ImageScannerColorMode]::Grayscale
            } elseif ($ColorMode -eq "Monochrome" -or $ColorMode -eq "BN") {
                $flatbed.ColorMode = [Windows.Devices.Scanners.ImageScannerColorMode]::Monochrome
            } else {
                $flatbed.ColorMode = [Windows.Devices.Scanners.ImageScannerColorMode]::Color
            }
        } catch {
            # Ignorar si el controlador de l'escàner no admet canvi de mode per programari
        }
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
