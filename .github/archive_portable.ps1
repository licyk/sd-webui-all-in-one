param (
    [string]$SoftwareName,
    [string]$Workspace,
    [string]$Source,
    [string]$SaveDst,
    [string]$Author
)

$build_time = (Get-Date).ToUniversalTime().AddHours(8).ToString("yyyyMMdd")
$package_name = "${SoftwareName}-${Author}-${build_time}"
$protable_name = "${package_name}-nightly.7z"
New-Item -ItemType Directory -Path "${SaveDst}" -Force
Move-Item -Path "${Source}" -Destination "${Workspace}/${package_name}" -Force
7z a -t7z -bsp1 -m0=lzma2 -mx=9 -mfb=128 -md=768m -ms=on -mf=BCJ2 "${SaveDst}/${SoftwareName}/${protable_name}" "${Workspace}/${package_name}"