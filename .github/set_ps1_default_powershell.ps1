<#
.SYNOPSIS
Sets the current user's .ps1 default opener to PowerShell on Windows 10/11.

.DESCRIPTION
Windows protects per-user default application choices with a UserChoice Hash:

	  HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.ps1\UserChoice
	    ProgID
	    Hash

	On newer Windows 11 builds, Explorer can also keep the latest selected ProgID at:

	  HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.ps1\UserChoiceLatest\ProgId
	    ProgId

	If ProgID is edited without a valid Hash, Windows treats it as tampering and
	resets or ignores the association. This script follows the same general approach
	Mozilla Firefox uses for its "set default browser" flow: generate the expected
	UserChoice Hash, delete and recreate the UserChoice key, then notify Explorer
	that associations changed. It also updates UserChoiceLatest\ProgId so Windows 11
	default-app UI and Explorer entry points do not keep pointing at the old ProgID.

This is intentionally marked experimental. The UserChoice Hash algorithm is not
a documented Microsoft API and may change in Windows updates. Microsoft supports
interactive default-app selection and managed default-association deployment, but
not arbitrary silent default-app changes by normal applications.

.IMPLEMENTATION NOTES
For file extensions, Firefox hashes this lower-cased string:

  extension + user SID + ProgID + FILETIME_UTC_HIGH + FILETIME_UTC_LOW +
  "User Choice set via Windows User Experience {D18B6DD5-6124-4341-9318-804003BAFA0B}"

The timestamp is rounded down to the current UTC minute. The generated Hash must
be written while Windows still sees the UserChoice key last-write time in that
same minute. This is why the script waits if it is too close to the next minute,
then generates the Hash immediately before recreating UserChoice.

The HashString routine below ports Firefox's MD5-derived 32-bit overflow
scramble. The numeric constants are copied from Firefox's implementation.

The -RegRename option mirrors Firefox's fallback for systems where a kernel
driver or protection layer interferes with UserChoice subkeys. It renames the
association key temporarily, edits UserChoice, then renames it back.

.INTEGRATION
This file can be dot-sourced as a small library:

  . .\Set-Ps1DefaultPowerShell.ps1
  Invoke-Ps1DefaultPowerShellConfiguration -Force

When dot-sourced, the script only defines functions. When executed normally, it
runs Invoke-Ps1DefaultPowerShellConfiguration with the script parameters.

.REFERENCES
Mozilla Firefox source:
  https://github.com/mozilla-firefox/firefox/blob/main/browser/components/shell/WindowsUserChoice.cpp
  https://github.com/mozilla-firefox/firefox/blob/main/toolkit/mozapps/defaultagent/SetDefaultBrowser.cpp

Microsoft default-app behavior:
  https://learn.microsoft.com/windows/apps/develop/windows-integration/default-apps-platform
  https://learn.microsoft.com/windows/compatibility/file-type-and-protocol-associations-model

Related reverse-engineered tools/notes referenced by Mozilla:
  https://github.com/DanysysTeam/PS-SFTA
  https://kolbi.cz/blog/2017/10/25/setuserfta-userchoice-hash-defeated-set-file-type-associations-per-user/
#>

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$Extension = ".ps1",
    [string]$ProgId = "Microsoft.PowerShellScript.1",
    [string]$PowerShellPath = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe",
    [switch]$RegRename,
    [switch]$Force
)

$script:UserChoiceNativeType = $null

function Initialize-UserChoiceNativeTypes {
    [CmdletBinding()]
    param()

    $existingNativeType = Get-Variable -Scope Script -Name "UserChoiceNativeType" -ErrorAction SilentlyContinue
    if ($null -ne $existingNativeType -and $existingNativeType.Value -is [type]) {
        return $existingNativeType.Value
    }

    # Add-Type cannot replace a previously loaded class in the same PowerShell
    # process. Use a unique class name so repeated script updates in one session
    # cannot accidentally keep running an older embedded C# implementation.
    $nativeTypeName = "UserChoiceNative_$([Guid]::NewGuid().ToString("N"))"

    $source = @"
using Microsoft.Win32;
using Microsoft.Win32.SafeHandles;
using System;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;

public static class __USER_CHOICE_NATIVE_TYPE__
{
    private const int ERROR_SUCCESS = 0;
    private const int SHCNE_ASSOCCHANGED = 0x08000000;
    private const int SHCNF_IDLIST = 0x0000;

    [StructLayout(LayoutKind.Sequential)]
    private struct FILETIME_NATIVE
    {
        public uint dwLowDateTime;
        public uint dwHighDateTime;
    }

    [DllImport("Advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern int RegRenameKey(
        IntPtr hKey,
        [MarshalAs(UnmanagedType.LPWStr)] string lpSubKeyName,
        [MarshalAs(UnmanagedType.LPWStr)] string lpNewKeyName);

    [DllImport("Advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern int RegQueryInfoKey(
        SafeRegistryHandle hKey,
        StringBuilder lpClass,
        ref uint lpcchClass,
        IntPtr lpReserved,
        out uint lpcSubKeys,
        out uint lpcbMaxSubKeyLen,
        out uint lpcbMaxClassLen,
        out uint lpcValues,
        out uint lpcbMaxValueNameLen,
        out uint lpcbMaxValueLen,
        out uint lpcbSecurityDescriptor,
        out FILETIME_NATIVE lpftLastWriteTime);

    [DllImport("Shell32.dll")]
    private static extern void SHChangeNotify(int wEventId, int uFlags, IntPtr dwItem1, IntPtr dwItem2);

    public static bool ProgIdExists(string progId)
    {
        using (RegistryKey key = Registry.ClassesRoot.OpenSubKey(progId, false))
        {
            return key != null;
        }
    }

    public static string GenerateHash(string association, string userSid, string progId, DateTime utcTimestamp)
    {
        if (utcTimestamp.Kind != DateTimeKind.Utc)
        {
            utcTimestamp = utcTimestamp.ToUniversalTime();
        }

        // Firefox zeros seconds and milliseconds before converting to FILETIME.
        // Windows compares against the UserChoice key last-write time rounded to
        // the same minute, so generation and registry write must stay close.
        utcTimestamp = new DateTime(
            utcTimestamp.Year,
            utcTimestamp.Month,
            utcTimestamp.Day,
            utcTimestamp.Hour,
            utcTimestamp.Minute,
            0,
            DateTimeKind.Utc);

        long fileTime = utcTimestamp.ToFileTimeUtc();
        uint low = unchecked((uint)(fileTime & 0xffffffffL));
        uint high = unchecked((uint)((fileTime >> 32) & 0xffffffffL));

        const string userExperience =
            "User Choice set via Windows User Experience {D18B6DD5-6124-4341-9318-804003BAFA0B}";

        // Firefox formats high FILETIME first, then low FILETIME, both as
        // lowercase 8-digit hex, and lowercases the full UTF-16 string.
        string input = string.Format(
            CultureInfo.InvariantCulture,
            "{0}{1}{2}{3:x8}{4:x8}{5}",
            association,
            userSid,
            progId,
            high,
            low,
            userExperience).ToLowerInvariant();

        return HashString(input);
    }

    public static void SetUserChoice(string association, string progId, string hash, bool regRename)
    {
        string path = GetAssociationKeyPath(association);

        using (RegistryKey assocKey = Registry.CurrentUser.CreateSubKey(path, true))
        {
            if (assocKey == null)
            {
                throw new InvalidOperationException("Could not open or create HKCU:\\" + path);
            }

            bool renamed = false;
            IntPtr handle = IntPtr.Zero;

            try
            {
                if (regRename)
                {
                    // Optional Firefox-style workaround: move the association
                    // key out of the protected name while rewriting UserChoice.
                    handle = assocKey.Handle.DangerousGetHandle();
                    string temporaryName = Guid.NewGuid().ToString("B");
                    int result = RegRenameKey(handle, null, temporaryName);
                    if (result != ERROR_SUCCESS)
                    {
                        throw new InvalidOperationException("RegRenameKey to temporary name failed: " + result);
                    }
                    renamed = true;
                }

                try
                {
                    // File association UserChoice keys can deny SetValue for
                    // the user. Deleting and recreating the subkey is the part
                    // that matters; editing values in place is often rejected.
                    assocKey.DeleteSubKey("UserChoice", false);
                }
                catch (ArgumentException)
                {
                    // Missing UserChoice is fine.
                }

                using (RegistryKey userChoice = assocKey.CreateSubKey("UserChoice", true))
                {
                    if (userChoice == null)
                    {
                        throw new InvalidOperationException("Could not create UserChoice key.");
                    }

                    userChoice.SetValue("ProgID", progId, RegistryValueKind.String);
                    userChoice.SetValue("Hash", hash, RegistryValueKind.String);
                }

                SetUserChoiceLatest(assocKey, progId);
            }
            finally
            {
                if (renamed)
                {
                    int result = RegRenameKey(handle, null, association);
                    if (result != ERROR_SUCCESS)
                    {
                        throw new InvalidOperationException("RegRenameKey back to association failed: " + result);
                    }
                }
            }
        }
    }

    private static void SetUserChoiceLatest(RegistryKey assocKey, string progId)
    {
        using (RegistryKey latestRoot = assocKey.CreateSubKey("UserChoiceLatest", true))
        {
            if (latestRoot == null)
            {
                throw new InvalidOperationException("Could not open or create UserChoiceLatest key.");
            }

            try
            {
                latestRoot.DeleteSubKey("ProgId", false);
            }
            catch (ArgumentException)
            {
                // Missing UserChoiceLatest\ProgId is fine.
            }

            using (RegistryKey latestProgId = latestRoot.CreateSubKey("ProgId", true))
            {
                if (latestProgId == null)
                {
                    throw new InvalidOperationException("Could not create UserChoiceLatest\\ProgId key.");
                }

                latestProgId.SetValue("ProgId", progId, RegistryValueKind.String);
            }
        }
    }

    public static string ValidateUserChoiceHash(string association, string userSid)
    {
        string path = GetAssociationKeyPath(association) + "\\UserChoice";

        using (RegistryKey key = Registry.CurrentUser.OpenSubKey(path, false))
        {
            if (key == null)
            {
                return "UserChoice key does not exist.";
            }

            string progId = key.GetValue("ProgID") as string;
            if (string.IsNullOrEmpty(progId))
            {
                progId = key.GetValue("ProgId") as string;
            }

            string storedHash = key.GetValue("Hash") as string;
            if (string.IsNullOrEmpty(progId) || string.IsNullOrEmpty(storedHash))
            {
                return "UserChoice is missing ProgID/ProgId or Hash.";
            }

            DateTime lastWriteUtc = GetRegistryKeyLastWriteTimeUtc(key);
            string computedHash = GenerateHash(association, userSid, progId, lastWriteUtc);

            if (StringComparer.Ordinal.Equals(storedHash, computedHash))
            {
                return "OK: stored Hash matches ProgID " + progId + ".";
            }

            return "Mismatch: stored ProgID=" + progId + ", stored Hash=" + storedHash +
                   ", computed Hash=" + computedHash + ".";
        }
    }

    public static string ValidateUserChoiceLatest(string association, string expectedProgId)
    {
        string path = GetAssociationKeyPath(association) + "\\UserChoiceLatest\\ProgId";

        using (RegistryKey key = Registry.CurrentUser.OpenSubKey(path, false))
        {
            if (key == null)
            {
                return "UserChoiceLatest\\ProgId key does not exist.";
            }

            string progId = key.GetValue("ProgId") as string;
            if (StringComparer.Ordinal.Equals(progId, expectedProgId))
            {
                return "OK: UserChoiceLatest ProgId matches " + expectedProgId + ".";
            }

            return "Mismatch: UserChoiceLatest ProgId=" + progId + ", expected ProgId=" + expectedProgId + ".";
        }
    }

    public static void NotifyAssociationChanged()
    {
        SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, IntPtr.Zero, IntPtr.Zero);
    }

    private static string GetAssociationKeyPath(string association)
    {
        if (association.StartsWith(".", StringComparison.Ordinal))
        {
            return @"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\" + association;
        }

        return @"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\" + association;
    }

    private static DateTime GetRegistryKeyLastWriteTimeUtc(RegistryKey key)
    {
        uint classLength = 0;
        uint subKeyCount;
        uint maxSubKeyLength;
        uint maxClassLength;
        uint valueCount;
        uint maxValueNameLength;
        uint maxValueLength;
        uint securityDescriptorLength;
        FILETIME_NATIVE lastWriteTime;

        int result = RegQueryInfoKey(
            key.Handle,
            null,
            ref classLength,
            IntPtr.Zero,
            out subKeyCount,
            out maxSubKeyLength,
            out maxClassLength,
            out valueCount,
            out maxValueNameLength,
            out maxValueLength,
            out securityDescriptorLength,
            out lastWriteTime);

        if (result != ERROR_SUCCESS)
        {
            throw new InvalidOperationException("RegQueryInfoKey failed: " + result);
        }

        long fileTime = ((long)lastWriteTime.dwHighDateTime << 32) | lastWriteTime.dwLowDateTime;
        return DateTime.FromFileTimeUtc(fileTime);
    }

    private static string HashString(string input)
    {
        // Include the terminating UTF-16 NUL, matching Firefox's lstrlenW + 1.
        byte[] inputBytes = Encoding.Unicode.GetBytes(input + "\0");
        int blockCount = inputBytes.Length / 8;
        if (blockCount == 0)
        {
            throw new InvalidOperationException("Hash input is too short.");
        }

        byte[] md5Bytes;
        using (MD5 md5 = MD5.Create())
        {
            md5Bytes = md5.ComputeHash(inputBytes);
        }

        uint md0 = BitConverter.ToUInt32(md5Bytes, 0);
        uint md1 = BitConverter.ToUInt32(md5Bytes, 4);

        // These constants are not derived here. They are the known UserChoice
        // hash constants used by Windows 10/11 and carried by Firefox.
        uint[,] c0s = new uint[,]
        {
            { md0 | 1u, 0xCF98B111u, 0x87085B9Fu, 0x12CEB96Du, 0x257E1D83u },
            { md1 | 1u, 0xA27416F5u, 0xD38396FFu, 0x7C932B89u, 0xBFA49F69u }
        };

        uint[,] c1s = new uint[,]
        {
            { md0 | 1u, 0xEF0569FBu, 0x689B6B9Fu, 0x79F8A395u, 0xC3EFEA97u },
            { md1 | 1u, 0xC31713DBu, 0xDDCD1F0Fu, 0x59C3AF2Du, 0x35BD1EC9u }
        };

        uint h0 = 0;
        uint h1 = 0;
        uint h0Acc = 0;
        uint h1Acc = 0;

        unchecked
        {
            for (int i = 0; i < blockCount; i++)
            {
                for (int j = 0; j < 2; j++)
                {
                    uint inputDword = BitConverter.ToUInt32(inputBytes, (i * 2 + j) * 4);

                    h0 += inputDword;
                    h0 *= c0s[j, 0];
                    h0 = WordSwap(h0) * c0s[j, 1];
                    h0 = WordSwap(h0) * c0s[j, 2];
                    h0 = WordSwap(h0) * c0s[j, 3];
                    h0 = WordSwap(h0) * c0s[j, 4];
                    h0Acc += h0;

                    h1 += inputDword;
                    h1 = WordSwap(h1) * c1s[j, 1] + h1 * c1s[j, 0];
                    h1 = (h1 >> 16) * c1s[j, 2] + h1 * c1s[j, 3];
                    h1 = WordSwap(h1) * c1s[j, 4] + h1;
                    h1Acc += h1;
                }
            }

            byte[] hashBytes = new byte[8];
            Array.Copy(BitConverter.GetBytes(h0 ^ h1), 0, hashBytes, 0, 4);
            Array.Copy(BitConverter.GetBytes(h0Acc ^ h1Acc), 0, hashBytes, 4, 4);
            return Convert.ToBase64String(hashBytes);
        }
    }

    private static uint WordSwap(uint value)
    {
        return (value >> 16) | (value << 16);
    }
}
"@

    $source = $source.Replace("__USER_CHOICE_NATIVE_TYPE__", $nativeTypeName)
    Add-Type -TypeDefinition $source -ErrorAction Stop | Out-Null
    $script:UserChoiceNativeType = $nativeTypeName -as [type]

    if ($null -eq $script:UserChoiceNativeType) {
        throw "Could not load generated native helper type '$nativeTypeName'."
    }

    return $script:UserChoiceNativeType
}

function Assert-DefaultAssociationEnvironment {
    [CmdletBinding()]
    param()

    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
        throw "This script only runs on Windows."
    }

    if ([Environment]::Is64BitOperatingSystem -and -not [Environment]::Is64BitProcess) {
        Write-Warning "You are running a 32-bit PowerShell process on 64-bit Windows. Use 64-bit PowerShell if the association does not take."
    }
}

function Normalize-FileExtension {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Extension
    )

    $normalizedExtension = $Extension.Trim().ToLowerInvariant()

    if ([string]::IsNullOrWhiteSpace($normalizedExtension)) {
        throw "Extension cannot be empty."
    }

    if (-not $normalizedExtension.StartsWith(".")) {
        throw "This script targets file extensions. Extension must start with '.', for example '.ps1'."
    }

    return $normalizedExtension
}

function Get-CurrentUserStringSid {
    [CmdletBinding()]
    param()

    return [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
}

function Test-ProgId {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$ProgId
    )

    $native = Initialize-UserChoiceNativeTypes
    return $native::ProgIdExists($ProgId)
}

function Get-PowerShellOpenCommand {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$PowerShellPath
    )

    if ([string]::IsNullOrWhiteSpace($PowerShellPath)) {
        throw "PowerShellPath cannot be empty."
    }

    if (-not (Test-Path -LiteralPath $PowerShellPath)) {
        throw "PowerShell executable was not found: $PowerShellPath"
    }

    return '"' + $PowerShellPath + '" -NoProfile -File "%1" %*'
}

function Set-ProgIdOpenCommand {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$ProgId,

        [Parameter(Mandatory = $true)]
        [string]$OpenCommand,

        [string]$FriendlyName = "Windows PowerShell Script"
    )

    $progIdKey = $null
    $shellKey = $null
    $commandKey = $null

    try {
        $progIdKey = [Microsoft.Win32.Registry]::CurrentUser.CreateSubKey("Software\Classes\$ProgId", $true)
        if ($null -eq $progIdKey) {
            throw "Could not open or create HKCU:\Software\Classes\$ProgId."
        }

        if (-not [string]::IsNullOrWhiteSpace($FriendlyName)) {
            $progIdKey.SetValue("", $FriendlyName, [Microsoft.Win32.RegistryValueKind]::String)
        }

        $shellKey = [Microsoft.Win32.Registry]::CurrentUser.CreateSubKey("Software\Classes\$ProgId\Shell", $true)
        if ($null -eq $shellKey) {
            throw "Could not open or create HKCU:\Software\Classes\$ProgId\Shell."
        }
        $shellKey.SetValue("", "Open", [Microsoft.Win32.RegistryValueKind]::String)

        $commandKey = [Microsoft.Win32.Registry]::CurrentUser.CreateSubKey("Software\Classes\$ProgId\Shell\Open\Command", $true)
        if ($null -eq $commandKey) {
            throw "Could not open or create HKCU:\Software\Classes\$ProgId\Shell\Open\Command."
        }
        $commandKey.SetValue("", $OpenCommand, [Microsoft.Win32.RegistryValueKind]::String)
    }
    finally {
        if ($null -ne $commandKey) {
            $commandKey.Dispose()
        }

        if ($null -ne $shellKey) {
            $shellKey.Dispose()
        }

        if ($null -ne $progIdKey) {
            $progIdKey.Dispose()
        }
    }
}

function Wait-UserChoiceHashWriteWindow {
    [CmdletBinding()]
    param(
        [int]$MinimumMillisecondsRemaining = 2000,
        [int]$SleepBufferMilliseconds = 200
    )

    $now = [DateTime]::UtcNow
    $millisecondsLeft = ((60 - $now.Second) * 1000) - $now.Millisecond

    if ($millisecondsLeft -le $MinimumMillisecondsRemaining) {
        Start-Sleep -Milliseconds ($millisecondsLeft + $SleepBufferMilliseconds)
    }
}

function Set-UserChoiceAssociation {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Extension,

        [Parameter(Mandatory = $true)]
        [string]$ProgId,

        [Parameter(Mandatory = $true)]
        [string]$UserSid,

        [switch]$RegRename
    )

    $native = Initialize-UserChoiceNativeTypes
    Wait-UserChoiceHashWriteWindow

    $hash = $native::GenerateHash($Extension, $UserSid, $ProgId, [DateTime]::UtcNow)
    $native::SetUserChoice($Extension, $ProgId, $hash, [bool]$RegRename)
    $native::NotifyAssociationChanged()

    return @(
        $native::ValidateUserChoiceHash($Extension, $UserSid)
        $native::ValidateUserChoiceLatest($Extension, $ProgId)
    )
}

function New-DefaultAssociationPlan {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Extension,

        [Parameter(Mandatory = $true)]
        [string]$ProgId,

        [Parameter(Mandatory = $true)]
        [string]$UserSid,

        [Parameter(Mandatory = $true)]
        [string]$OpenCommand,

        [switch]$RegRename
    )

    return [pscustomobject]@{
        Extension = $Extension
        ProgId = $ProgId
        UserSid = $UserSid
        OpenCommand = $OpenCommand
        RegRename = [bool]$RegRename
    }
}

function Write-DefaultAssociationPlan {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [pscustomobject]$Plan
    )

    Write-Host "Target extension : $($Plan.Extension)"
    Write-Host "Target ProgID    : $($Plan.ProgId)"
    Write-Host "Current user SID : $($Plan.UserSid)"
    Write-Host "Open command     : $($Plan.OpenCommand)"
    Write-Host "RegRename        : $($Plan.RegRename)"
}

function Invoke-Ps1DefaultPowerShellConfiguration {
    [CmdletBinding(SupportsShouldProcess = $true)]
    param(
        [string]$Extension = ".ps1",
        [string]$ProgId = "Microsoft.PowerShellScript.1",
        [string]$PowerShellPath = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe",
        [switch]$RegRename,
        [switch]$Force
    )

    Set-StrictMode -Version Latest
    $ErrorActionPreference = "Stop"

    Assert-DefaultAssociationEnvironment
    $null = Initialize-UserChoiceNativeTypes

    $normalizedExtension = Normalize-FileExtension -Extension $Extension
    $openCommand = Get-PowerShellOpenCommand -PowerShellPath $PowerShellPath
    $progIdExists = Test-ProgId -ProgId $ProgId

    $plan = New-DefaultAssociationPlan `
        -Extension $normalizedExtension `
        -ProgId $ProgId `
        -UserSid (Get-CurrentUserStringSid) `
        -OpenCommand $openCommand `
        -RegRename:$RegRename

    Write-DefaultAssociationPlan -Plan $plan

    if (-not $progIdExists) {
        if ($Force) {
            Write-Warning "ProgID '$ProgId' does not exist under HKCR. It will be registered under HKCU before UserChoice is written."
        }
        else {
            Write-Warning "ProgID '$ProgId' does not exist under HKCR. Re-run with -Force to register it under HKCU and write UserChoice."
        }
    }

    if (-not $Force) {
        Write-Host ""
        Write-Host "Preview only. Re-run with -Force to write HKCU UserChoice and HKCU ProgID open command."
        return
    }

    if ($PSCmdlet.ShouldProcess("$normalizedExtension -> $ProgId", "write current-user default file association")) {
        # This defines what happens after UserChoice resolves .ps1 to the ProgID.
        Set-ProgIdOpenCommand -ProgId $ProgId -OpenCommand $openCommand

        $validation = Set-UserChoiceAssociation `
            -Extension $normalizedExtension `
            -ProgId $ProgId `
            -UserSid $plan.UserSid `
            -RegRename:$RegRename

        $validation | ForEach-Object { Write-Host $_ }
    }
}

if ($MyInvocation.InvocationName -ne ".") {
    Invoke-Ps1DefaultPowerShellConfiguration @PSBoundParameters
}
