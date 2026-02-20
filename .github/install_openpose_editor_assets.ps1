param (
    [string]$InstallPath = (Join-Path $PSScriptRoot "bin")
)

$temp_path = (Join-Path $([System.IO.Path]::GetTempPath()) $(Get-Random))
$install_path = $InstallPath
$url = "https://github.com/huchenlei/sd-webui-openpose-editor/releases/download/v0.3.0/dist.zip"
$archive_path = Join-Path $temp_path "dist_archive.zip"
$expand_path = Join-Path $temp_path "editor_dist"

if (!(Test-Path $temp_path)) {
    New-Item -ItemType Directory -Path $temp_path -Force
}

try {
    $web_request_params = @{
        Uri = $url
        UseBasicParsing = $true
        OutFile = $archive_path
    }
    Invoke-WebRequest @web_request_params
    Expand-Archive -Path $archive_path -DestinationPath $expand_path -Force
    Move-Item -Path $expand_path -Destination $install_path -Force
}
catch {
    Write-Error "安装 OpenPose Editor 资源出现错误: $_"
}
