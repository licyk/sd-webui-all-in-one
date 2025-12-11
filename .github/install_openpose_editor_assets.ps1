param (
    [string]$TempPath,
    [string]$InstallPath
)

$temp_path = $TempPath
$install_path = $InstallPath
$url = "https://github.com/huchenlei/sd-webui-openpose-editor/releases/download/v0.3.0/dist.zip"
$archive_path = "${temp_path}/dist_archive.zip"
$expand_path = "${temp_path}/editor_dist"

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
    Write-Host "安装 OpenPose Editor 资源出现错误: $_"
}
