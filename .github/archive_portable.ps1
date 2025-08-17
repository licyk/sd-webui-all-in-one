param (
    [string]$SoftwareName,
    [string]$Workspace,
    [string]$Source,
    [string]$SaveDst,
    [string]$Author,
    [switch]$ExtremeCompress
)

$build_time = (Get-Date).ToUniversalTime().AddHours(8).ToString("yyyyMMdd")
$package_name = "${SoftwareName}-${Author}-${build_time}"
$protable_name = "${package_name}-nightly.7z"
$save_path = "${SaveDst}/${SoftwareName}/${protable_name}"
$resource_path = "${Workspace}/${package_name}"
New-Item -ItemType Directory -Path "${SaveDst}" -Force
Move-Item -Path "${Source}" -Destination "${Workspace}/${package_name}" -Force
if ($ExtremeCompress) {
    Write-Host "使用极限压缩模式, 压缩 ${resource_path} 中"
    Write-Warning "压缩时间将大大增加"
    7z a -t7z -bsp1 -m0=lzma2 -mx=9 -mfb=128 -md=768m -ms=on -mf=BCJ2 "${save_path}" "${resource_path}"
} else {
    Write-Host "使用常规压缩模式, 压缩 ${resource_path} 中"
    7z a -t7z -bsp1 "${save_path}" "${resource_path}"
}
Write-Host "文件压缩完成, 保存在 ${save_path}"