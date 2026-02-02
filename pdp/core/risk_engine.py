import datetime
import json
import logging

logger = logging.getLogger("auth_service.core.risk_engine")

# WEIGHTS RECALCULATED
# Posture: 50%
# Context (Location/Travel + Time): 30%
# IP Reputation: 20%
WEIGHT_POSTURE = 0.50
WEIGHT_CONTEXT = 0.30
WEIGHT_IP_REP = 0.20

# Mock Threat Intel (Bad Verified IPs)
THREAT_INTEL_BLACKLIST = ["192.168.1.66", "10.0.0.66"] 

def calculate_risk_score(user, device, context: dict):
    """
    Calculates trust score (0-100) based on weighted factors.
    context: {
        "ip_address": str,
        "user_agent": str,
        "last_login_ip": str,
        "last_login_time": datetime
    }
    """
    score = 0
    details = {}

    # 1. Device Posture (50%)
    posture_score = 0.0
    
    # Check Freshness (e.g., last 2 minutes)
    is_fresh = False
    if device and device.last_posture_time:
        now = datetime.datetime.utcnow()
        # Ensure we handle potential timezone naiveness if SQLite/Postgres differs, 
        # but typically utcnow() vs stored UTC is fine.
        diff = (now - device.last_posture_time).total_seconds()
        if diff < 120: # 2 minutes freshness
            is_fresh = True
        else:
             logger.warning(f"Posture Report Expired for {user.username}. Age: {diff}s")

    if device and device.last_posture_report and is_fresh:
        try:
            report = json.loads(device.last_posture_report)
            checks_passed = 0
            total_checks = 0
            
            # Only check what agent actually reports
            if "firewall_enabled" in report:
                total_checks += 1
                if report["firewall_enabled"]: checks_passed += 1
            if "antivirus_enabled" in report:
                total_checks += 1
                if report["antivirus_enabled"]: checks_passed += 1

            posture_score = (checks_passed / total_checks) * 100 if total_checks > 0 else 0 # Default 0 if empty
        except:
            posture_score = 0
    else:
        # Default for unknown or stale posture
        posture_score = 0 # STRICT: If no fresh report, trust is 0 on this component.

    score += posture_score * WEIGHT_POSTURE
    details["posture"] = int(posture_score)

    # 2. Context (Location + Time) (30%)
    context_score = 100
    
    current_ip = context.get("ip_address")
    last_ip = context.get("last_login_ip")
    last_time = context.get("last_login_time")
    
    # A. Impossible Travel (Velocity)
    if last_ip and last_time and current_ip and current_ip != last_ip:
        now = datetime.datetime.utcnow()
        time_diff = (now - last_time).total_seconds() / 3600.0 # hours
        
        # If IP changed in under 10 mins (0.16h)
        if time_diff < 0.16:
             context_score = 50 # PENALTY (Reduced from 0 to ensure we land in MFA range, not Block)
             logger.warning(f"Impossible Travel: {last_ip} -> {current_ip} in {time_diff*60:.1f} mins")
    
    # B. Time Check removed per user request
    # Context score is now primarily based on impossible travel check
        
    score += context_score * WEIGHT_CONTEXT
    details["context"] = int(context_score)
    
    # 3. IP Reputation (20%)
    # CRITICAL: If IP is blacklisted, we override everything to BLOCK.
    if current_ip in THREAT_INTEL_BLACKLIST:
        logger.warning(f"Malicious IP Detected: {current_ip}. Forcing Risk Score to 0.")
        return 0, {"ip_reputation": 0, "reason": "MALICIOUS_IP"}
        
    ip_rep_score = 100
    score += ip_rep_score * WEIGHT_IP_REP
    details["ip_reputation"] = ip_rep_score
    
    total_score = int(score)
    logger.info(f"Risk Calculation for {user.username}: {total_score} - Details: {details}")
    
    return total_score, details


def evaluate_posture_change(new_report: dict) -> tuple:
    """
    Evaluates a new posture report and determines if session should be terminated.
    
    Args:
        new_report: dict with posture data from agent
        
    Returns:
        (should_disconnect: bool, reason: str or None)
    """
    violations = []
    
    # Check Firewall
    if "firewall_enabled" in new_report and not new_report["firewall_enabled"]:
        violations.append("Firewall disabled")
    
    # Check Antivirus
    if "antivirus_enabled" in new_report and not new_report["antivirus_enabled"]:
        violations.append("Antivirus not active")
    
    # Check OS Health (optional)
    if "os_healthy" in new_report and not new_report["os_healthy"]:
        violations.append("OS health check failed")
    
    if violations:
        reason = "; ".join(violations)
        logger.warning(f"Posture Violation Detected: {reason}")
        return True, reason
    
    return False, None
