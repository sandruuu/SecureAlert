<#
.SYNOPSIS
    SecureAlert Posture Agent - Continuous device health monitoring
    
.DESCRIPTION
    This script runs on Windows clients to monitor device security posture.
    It reports to the backend every 30 seconds and will notify the user
    if their session is terminated due to policy violations.
    
.NOTES
    Part of the Zero Trust Network Access (ZTNA) implementation
    
.EXAMPLE
    # First time enrollment (with token from dashboard)
    .\posture_agent.ps1 -EnrollToken "abc123..." -BackendUrl "http://localhost:8095"
    
    # Subsequent runs (uses cached credentials)
    .\posture_agent.ps1 -BackendUrl "http://localhost:8095"
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$EnrollToken,
    
    [Parameter(Mandatory=$false)]
    [string]$DeviceId,
    
    [Parameter(Mandatory=$false)]
    [string]$DeviceSecret,
    
    [Parameter(Mandatory=$false)]
    [string]$BackendUrl = "http://localhost:8095",
    
    [Parameter(Mandatory=$false)]
    [int]$IntervalSeconds = 30
)

# ============================================
# CONFIGURATION
# ============================================
$CacheDir = "$env:APPDATA\SecureAlert"
$CacheFile = "$CacheDir\agent_credentials.json"

# ============================================
# ENROLLMENT & CACHE FUNCTIONS
# ============================================

function Get-HardwareFingerprint {
    <#
    .SYNOPSIS
        Generates a unique hardware fingerprint for this machine
    #>
    try {
        $hostname = $env:COMPUTERNAME
        $cpu = (Get-CimInstance Win32_Processor | Select-Object -First 1).ProcessorId
        $disk = (Get-CimInstance Win32_DiskDrive | Select-Object -First 1).SerialNumber
        
        # Combine and hash
        $raw = "$hostname`:$cpu`:$disk"
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($raw)
        $hash = [System.Security.Cryptography.SHA256]::Create().ComputeHash($bytes)
        $fingerprint = "$hostname`:" + [BitConverter]::ToString($hash).Replace("-", "").Substring(0, 16).ToLower()
        
        return $fingerprint
    } catch {
        # Fallback to hostname + random if hardware info fails
        return "$env:COMPUTERNAME`:fallback_$([guid]::NewGuid().ToString().Substring(0,8))"
    }
}

function Save-Credentials {
    param(
        [string]$DeviceId,
        [string]$DeviceSecret,
        [string]$DeviceName
    )
    
    if (-not (Test-Path $CacheDir)) {
        New-Item -ItemType Directory -Path $CacheDir -Force | Out-Null
    }
    
    $creds = @{
        device_id = $DeviceId
        device_secret = $DeviceSecret
        device_name = $DeviceName
        enrolled_at = (Get-Date).ToString("o")
    }
    
    $creds | ConvertTo-Json | Set-Content -Path $CacheFile -Encoding UTF8
    Write-Host "Credentials saved to: $CacheFile" -ForegroundColor Green
}

function Get-CachedCredentials {
    if (Test-Path $CacheFile) {
        try {
            $creds = Get-Content $CacheFile -Raw | ConvertFrom-Json
            return @{
                DeviceId = $creds.device_id
                DeviceSecret = $creds.device_secret
                DeviceName = $creds.device_name
            }
        } catch {
            Write-Warning "Failed to read cached credentials: $_"
            return $null
        }
    }
    return $null
}

function Invoke-Enrollment {
    <#
    .SYNOPSIS
        Enrolls this device with the backend using an enrollment token
    #>
    param(
        [string]$BackendUrl,
        [string]$Token
    )
    
    $fingerprint = Get-HardwareFingerprint
    Write-Host "Hardware Fingerprint: $fingerprint" -ForegroundColor Cyan
    
    $enrollUrl = "$BackendUrl/api/agent/enroll"
    
    $body = @{
        token = $Token
        hardware_fingerprint = $fingerprint
    } | ConvertTo-Json
    
    try {
        $response = Invoke-RestMethod -Uri $enrollUrl -Method POST `
                                      -Body $body -ContentType "application/json" `
                                      -ErrorAction Stop
        
        if ($response.status -eq "ok") {
            Save-Credentials -DeviceId $response.device_id `
                            -DeviceSecret $response.device_secret `
                            -DeviceName $response.device_name
            
            return @{
                DeviceId = $response.device_id
                DeviceSecret = $response.device_secret
                DeviceName = $response.device_name
            }
        } else {
            Write-Error "Enrollment failed: $($response.message)"
            return $null
        }
    } catch {
        Write-Error "Enrollment request failed: $_"
        return $null
    }
}

# ============================================
# HELPER FUNCTIONS
# ============================================


function Get-PostureData {
    <#
    .SYNOPSIS
        Collects device posture information
    #>
    
    $posture = @{
        os_version = ""
        os_healthy = $true
        firewall_enabled = $false
        antivirus_enabled = $false
    }
    
    try {
        # 1. OS Version
        $os = Get-CimInstance Win32_OperatingSystem
        $posture.os_version = "$($os.Caption) Build $($os.BuildNumber)"
        
        # OS Health: Check if version is supported (Windows 10/11)
        $posture.os_healthy = $os.BuildNumber -ge 19041  # Windows 10 2004+
    } catch {
        Write-Warning "Failed to get OS info: $_"
        $posture.os_healthy = $false
    }
    
    try {
        # 2. Firewall Status (All profiles must be enabled)
        $firewallProfiles = Get-NetFirewallProfile
        $allEnabled = ($firewallProfiles | Where-Object { $_.Enabled -eq $true }).Count -eq 3
        $posture.firewall_enabled = $allEnabled
    } catch {
        Write-Warning "Failed to get Firewall status: $_"
        $posture.firewall_enabled = $false
    }
    
    try {
        # 3. Antivirus Status (Windows Defender)
        $defenderStatus = Get-MpComputerStatus -ErrorAction SilentlyContinue
        if ($defenderStatus) {
            $posture.antivirus_enabled = $defenderStatus.AntivirusEnabled -and 
                                          -not $defenderStatus.RealTimeProtectionEnabled -eq $false
        } else {
            # Fallback: Check Windows Security Center
            $avProduct = Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntiVirusProduct -ErrorAction SilentlyContinue
            $posture.antivirus_enabled = $null -ne $avProduct
        }
    } catch {
        Write-Warning "Failed to get Antivirus status: $_"
        $posture.antivirus_enabled = $false
    }
    
    return $posture
}

function New-HmacSignature {
    <#
    .SYNOPSIS
        Creates HMAC-SHA256 signature for the posture report
    #>
    param(
        [string]$DeviceId,
        [int]$Timestamp,
        [string]$Nonce,
        [hashtable]$Posture,
        [string]$Secret
    )
    
    # Convert posture to JSON with sorted keys (match Python's sort_keys=True)
    # Python json.dumps format: {"key": value, "key2": value} (space after : and ,)
    $sortedKeys = $Posture.Keys | Sort-Object
    $jsonParts = @()
    foreach ($key in $sortedKeys) {
        $value = $Posture[$key]
        if ($value -is [bool]) {
            $jsonValue = if ($value) { "true" } else { "false" }
        } elseif ($value -is [int] -or $value -is [double]) {
            $jsonValue = $value.ToString()
        } else {
            $jsonValue = "`"$value`""
        }
        $jsonParts += "`"$key`": $jsonValue"  # Space after colon
    }
    $postureJson = "{" + ($jsonParts -join ", ") + "}"  # Space after comma
    
    # Construct message (must match backend format exactly)
    $message = "$DeviceId`:$Timestamp`:$Nonce`:$postureJson"
    
    # Create HMAC-SHA256
    $hmac = New-Object System.Security.Cryptography.HMACSHA256
    $hmac.Key = [System.Text.Encoding]::UTF8.GetBytes($Secret)
    $hash = $hmac.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($message))
    
    # Return hex string
    return [BitConverter]::ToString($hash).Replace("-", "").ToLower()
}



function Send-PostureReport {
    <#
    .SYNOPSIS
        Sends posture report to backend with HMAC signature
    #>
    param(
        [string]$BackendUrl,
        [string]$DeviceId,
        [string]$DeviceSecret,
        [hashtable]$Posture
    )
    
    $timestamp = [int][DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    $nonce = [guid]::NewGuid().ToString()
    
    $signature = New-HmacSignature -DeviceId $DeviceId -Timestamp $timestamp `
                                   -Nonce $nonce -Posture $Posture -Secret $DeviceSecret
    
    $body = @{
        device_id = $DeviceId
        timestamp = $timestamp
        nonce = $nonce
        posture = $Posture
        signature = $signature
    } | ConvertTo-Json -Depth 3
    
    try {
        $response = Invoke-RestMethod -Uri $BackendUrl -Method POST `
                                      -Body $body -ContentType "application/json" `
                                      -ErrorAction Stop
        return $response
    } catch {
        Write-Warning "Failed to send posture report: $_"
        return $null
    }
}

function Show-DisconnectNotification {
    <#
    .SYNOPSIS
        Shows Windows notification when session is terminated
    #>
    param([string]$Reason)
    
    Add-Type -AssemblyName System.Windows.Forms
    
    $notification = New-Object System.Windows.Forms.NotifyIcon
    $notification.Icon = [System.Drawing.SystemIcons]::Warning
    $notification.BalloonTipIcon = [System.Windows.Forms.ToolTipIcon]::Error
    $notification.BalloonTipTitle = "SecureAlert - Session Terminated"
    $notification.BalloonTipText = "Your session was terminated due to: $Reason`n`nPlease address the issue and reconnect."
    $notification.Visible = $true
    $notification.ShowBalloonTip(10000)
    
    Start-Sleep -Seconds 10
    $notification.Dispose()
}

function Get-DeviceCredentials {
    <#
    .SYNOPSIS
        Fetches device credentials from backend using session cookie
    #>
    param(
        [string]$BackendUrl,
        [string]$SessionCookie
    )
    
    $credentialsUrl = "$BackendUrl/api/user/device/credentials"
    
    try {
        $headers = @{
            "Cookie" = "session_id=$SessionCookie"
        }
        
        $response = Invoke-RestMethod -Uri $credentialsUrl -Method GET `
                                      -Headers $headers -ErrorAction Stop
        
        return @{
            DeviceId = $response.device_id
            DeviceSecret = $response.device_secret
            DeviceName = $response.device_name
        }
    } catch {
        Write-Error "Failed to fetch device credentials: $_"
        return $null
    }
}

# ============================================
# MAIN LOOP
# ============================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " SecureAlert Posture Agent v2.0" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Determine credentials source (priority order)
$creds = $null

# 1. Try enrollment with token (highest priority)
if ($EnrollToken) {
    Write-Host "Mode: Enrollment with token" -ForegroundColor Green
    Write-Host "Enrolling device..." -ForegroundColor Yellow
    
    $creds = Invoke-Enrollment -BackendUrl $BackendUrl -Token $EnrollToken
    
    if (-not $creds) {
        Write-Host "ERROR: Enrollment failed. Token may be invalid or expired." -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Enrollment successful!" -ForegroundColor Green
    Write-Host "Device: $($creds.DeviceName)" -ForegroundColor Cyan
}
# 2. Try cached credentials
elseif (-not $DeviceId -or -not $DeviceSecret) {
    Write-Host "Checking for cached credentials..." -ForegroundColor Yellow
    $creds = Get-CachedCredentials
    
    if ($creds) {
        Write-Host "Mode: Using cached credentials" -ForegroundColor Green
        Write-Host "Device: $($creds.DeviceName)" -ForegroundColor Cyan
    }
}

# 3. Use manual credentials if provided
if ($DeviceId -and $DeviceSecret) {
    Write-Host "Mode: Manual credentials" -ForegroundColor Yellow
    $creds = @{
        DeviceId = $DeviceId
        DeviceSecret = $DeviceSecret
        DeviceName = "Manual Device"
    }
}

# 4. Final check - do we have credentials?
if (-not $creds) {
    Write-Host ""
    Write-Host "ERROR: No credentials found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "To use this agent, you need to enroll first:" -ForegroundColor Yellow
    Write-Host "1. Log in to SecureAlert dashboard" -ForegroundColor Gray
    Write-Host "2. Copy the enrollment token shown after login" -ForegroundColor Gray
    Write-Host "3. Run: .\posture_agent.ps1 -EnrollToken 'your-token-here'" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Or provide manual credentials:" -ForegroundColor Yellow
    Write-Host ".\posture_agent.ps1 -DeviceId 'id' -DeviceSecret 'secret'" -ForegroundColor Gray
    exit 1
}

# Set credentials for use
$DeviceId = $creds.DeviceId
$DeviceSecret = $creds.DeviceSecret

Write-Host ""
Write-Host "Device ID: $DeviceId" -ForegroundColor Yellow
Write-Host "Backend: $BackendUrl" -ForegroundColor Yellow
Write-Host "Interval: ${IntervalSeconds}s" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press Ctrl+C to stop..." -ForegroundColor Gray
Write-Host ""

try {
    while ($true) {
        # Collect posture data
        $posture = Get-PostureData
        
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Collecting posture..." -NoNewline
        Write-Host " Firewall: $($posture.firewall_enabled)" -NoNewline -ForegroundColor $(if ($posture.firewall_enabled) { "Green" } else { "Red" })
        Write-Host " AV: $($posture.antivirus_enabled)" -ForegroundColor $(if ($posture.antivirus_enabled) { "Green" } else { "Red" })
        
        # Send report
        $postureUrl = "$BackendUrl/api/user/posture/report"
        $response = Send-PostureReport -BackendUrl $postureUrl `
                                       -DeviceId $DeviceId `
                                       -DeviceSecret $DeviceSecret `
                                       -Posture $posture
        
        if ($response) {
            if ($response.status -eq "disconnect") {
                Write-Host "[$(Get-Date -Format 'HH:mm:ss')] SESSION TERMINATED: $($response.reason)" -ForegroundColor Red
                Show-DisconnectNotification -Reason $response.reason
                Write-Host "Exiting agent due to posture violation." -ForegroundColor Red
                # exit 1  <-- REMOVED: Keep agent running so it can recover when issues are fixed
                Write-Host "Agent will continue running. Please fix the issues above to restore access." -ForegroundColor Yellow
            } else {
                Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Report sent successfully." -ForegroundColor Green
            }
        } else {
            Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Failed to send report (backend unreachable?)" -ForegroundColor Yellow
        }
        
        Start-Sleep -Seconds $IntervalSeconds
    }
} catch {
    Write-Host "Agent stopped: $_" -ForegroundColor Red
}
