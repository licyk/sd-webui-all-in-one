param (
    [Parameter(Mandatory = $true)]
    [ValidatePattern("_(cuda|rocm|xpu|mps)$")]
    [string]$SoftwareName,
    [Parameter(Mandatory = $true)][string]$Workspace,
    [Parameter(Mandatory = $true)][string]$Source,
    [Parameter(Mandatory = $true)][string]$SaveDst,
    [Parameter(Mandatory = $true)][string]$Author,
    [ValidateSet("windows", "linux", "macos")]
    [string]$Platform = "windows",
    [ValidateSet("auto", "7z", "tar.gz")]
    [string]$ArchiveFormat = "auto",
    [switch]$ExtremeCompress,
    [string]$OutputFile
)

$build_time = (Get-Date).ToUniversalTime().AddHours(8).ToString("yyyyMMdd")
$platform_name = $Platform.ToLowerInvariant()
$package_name = "${SoftwareName}-${Author}-${platform_name}-${build_time}"
$archive_format_name = if ($ArchiveFormat -eq "auto") {
    if ($Platform -eq "windows") { "7z" } else { "tar.gz" }
} else {
    $ArchiveFormat
}
$portable_name = "${package_name}-nightly.${archive_format_name}"
$save_dir = Join-Path $SaveDst $SoftwareName
$save_path = Join-Path $save_dir $portable_name
$resource_path = Join-Path $Workspace $package_name

New-Item -ItemType Directory -Path $save_dir -Force | Out-Null
Move-Item -LiteralPath $Source -Destination $resource_path -Force

if ($archive_format_name -eq "7z") {
    if ($ExtremeCompress) {
        Write-Host "使用极限压缩模式, 压缩 ${resource_path} 中"
        Write-Warning "压缩时间将大大增加"
        & 7z a -t7z -bsp1 -m0=lzma2 -mx=9 -mfb=128 -md=768m -ms=on -mf=BCJ2 $save_path $resource_path
    } else {
        Write-Host "使用常规压缩模式, 压缩 ${resource_path} 中"
        & 7z a -t7z -bsp1 $save_path $resource_path
    }
} else {
    if ($ExtremeCompress) {
        Write-Warning "tar.gz 归档不支持 ExtremeCompress, 将使用常规压缩"
    }
    Write-Host "使用 tar.gz 压缩 ${resource_path} 中"
    & tar -czf $save_path -C $Workspace $package_name
}

if ($LASTEXITCODE -ne 0) {
    throw "压缩便携包失败, 命令退出码: $LASTEXITCODE"
}

$resolved_save_path = (Resolve-Path -LiteralPath $save_path).Path
if ($OutputFile) {
    "archive-path=$resolved_save_path" | Out-File -LiteralPath $OutputFile -Encoding utf8 -Append
}
Write-Host "文件压缩完成, 保存在 ${resolved_save_path}"
Write-Output $resolved_save_path
