param (
    [string]$VAEApproxPath
)

$model_list = @(
    "https://huggingface.co/licyk/sd-vae/resolve/main/vae-approx/model.pt",
    "https://huggingface.co/licyk/sd-vae/resolve/main/vae-approx/vaeapprox-sd3.pt",
    "https://huggingface.co/licyk/sd-vae/resolve/main/vae-approx/vaeapprox-sdxl.pt"
)

$vae_approx_path = $VAEApproxPath
New-Item -ItemType Directory -Path "$vae_approx_path" -Force

ForEach ($url in $model_list) {
    $filename = Split-Path $url -Leaf
    $model_path = Join-Path -Path $vae_approx_path -ChildPath $filename
    if (Test-Path $model_path) {
        Write-Host "$filename 已存在于 $vae_approx_path"
    } else {
        Write-Host "下载 $filename 到 $vae_approx_path 中"
            $web_request_params = @{
            Uri = $url
            UseBasicParsing = $true
            OutFile = $model_path
        }
        Invoke-WebRequest @web_request_params
    }
}
