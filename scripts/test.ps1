$ErrorActionPreference = "Stop"

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$currentSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$sha256 = [System.Security.Cryptography.SHA256]::Create()
try {
    $sidHashBytes = $sha256.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($currentSid))
    $sidHash = ([BitConverter]::ToString($sidHashBytes) -replace "-", "").Substring(0, 12).ToLowerInvariant()
}
finally {
    $sha256.Dispose()
}
$pytestTempRoot = Join-Path $repoRoot "tmp\pytest\$sidHash"
$uvCacheRoot = Join-Path $repoRoot ".uv-cache"
$previousPytestTempRoot = [Environment]::GetEnvironmentVariable(
    "PYTEST_DEBUG_TEMPROOT",
    [EnvironmentVariableTarget]::Process
)
$pytestExitCode = 1

New-Item -ItemType Directory -Force -Path $pytestTempRoot | Out-Null

Push-Location -LiteralPath $repoRoot
try {
    # SID 分区避免不同 Windows 执行身份因同名用户目录和所有者专用 ACL 互相阻塞。
    # 分区内继续使用 pytest 自带的按运行编号隔离，保证并发安全和失败现场保留。
    [Environment]::SetEnvironmentVariable(
        "PYTEST_DEBUG_TEMPROOT",
        $pytestTempRoot,
        [EnvironmentVariableTarget]::Process
    )

    & uv --cache-dir $uvCacheRoot run --group dev pytest -q -p no:cacheprovider @args
    $pytestExitCode = $LASTEXITCODE
}
finally {
    [Environment]::SetEnvironmentVariable(
        "PYTEST_DEBUG_TEMPROOT",
        $previousPytestTempRoot,
        [EnvironmentVariableTarget]::Process
    )
    Pop-Location
}

exit $pytestExitCode
