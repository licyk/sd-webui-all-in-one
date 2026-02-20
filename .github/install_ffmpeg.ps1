param (
    [string]$InstallPath = (Join-Path $PSScriptRoot "bin")
)
$url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-full.7z"
$dst_path = $InstallPath
$temp_path = New-Item -ItemType Directory -Path (Join-Path $([System.IO.Path]::GetTempPath()) "ffmpeg_dl_$(Get-Random)") -Force
$archive_path = Join-Path $temp_path "ffmpeg.7z"

try {
    if (!(Test-Path $dst_path)) {
        New-Item -ItemType Directory -Path $dst_path -Force | Out-Null
    }

    Write-Host "正在下载 FFmpeg"
    $web_request_params = @{
        Uri = $url
        UseBasicParsing = $true
        OutFile = $archive_path
    }
    Invoke-WebRequest @web_request_params

    Write-Host "正在提取核心程序"
    & 7z e "$archive_path" "-o$($temp_path.FullName)" "ffmpeg.exe" "ffplay.exe" "ffprobe.exe" -r -y

    Write-Host "正在整理文件到 $dst_path"
    $extractedFiles = Get-ChildItem -Path $temp_path -Filter "*.exe"
    foreach ($file in $extractedFiles) {
        Move-Item -Path $file.FullName -Destination $dst_path -Force
    }

    Write-Host "FFmpeg 安装完成"
}
catch {
    Write-Error "发生错误: $($_.Exception.Message)"
}
finally {
    Write-Host "正在清理临时文件夹" -ForegroundColor Gray
    if (Test-Path $temp_path) {
        Remove-Item -Path $temp_path -Recurse -Force
    }
}