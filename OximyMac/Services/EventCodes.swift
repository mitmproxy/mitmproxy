import Foundation
import Sentry

enum LogLevel: String, Comparable {
    case debug
    case info
    case warning
    case error
    case fatal

    static func < (lhs: LogLevel, rhs: LogLevel) -> Bool {
        lhs.order < rhs.order
    }

    var order: Int {
        switch self {
        case .debug: return 0
        case .info: return 1
        case .warning: return 2
        case .error: return 3
        case .fatal: return 4
        }
    }
}

enum ActionCategory: String {
    case none
    case monitor
    case autoRetry = "auto_retry"
    case selfHealing = "self_healing"
    case investigate
    case alertOps = "alert_ops"
    case userAction = "user_action"
}

enum EventCode: String {
    // App
    case APP_INIT_001 = "APP.INIT.001"
    case APP_STATE_101 = "APP.STATE.101"
    case APP_START_001 = "APP.START.001"
    case APP_STOP_001 = "APP.STOP.001"
    case APP_FAIL_301 = "APP.FAIL.301"

    // Auth
    case AUTH_AUTH_001 = "AUTH.AUTH.001"
    case AUTH_AUTH_002 = "AUTH.AUTH.002"
    case AUTH_AUTH_004 = "AUTH.AUTH.004"
    case AUTH_FAIL_201 = "AUTH.FAIL.201"
    case AUTH_FAIL_301 = "AUTH.FAIL.301"
    case AUTH_FAIL_302 = "AUTH.FAIL.302"
    case AUTH_FAIL_303 = "AUTH.FAIL.303"

    // Enrollment
    case ENROLL_STATE_101 = "ENROLL.STATE.101"
    case ENROLL_FAIL_301 = "ENROLL.FAIL.301"

    // Certificate
    case CERT_STATE_101 = "CERT.STATE.101"
    case CERT_STATE_102 = "CERT.STATE.102"
    case CERT_STATE_105 = "CERT.STATE.105"
    case CERT_CHECK_003 = "CERT.CHECK.003"
    case CERT_WARN_201 = "CERT.WARN.201"
    case CERT_FAIL_301 = "CERT.FAIL.301"
    case CERT_FAIL_303 = "CERT.FAIL.303"

    // Proxy
    case PROXY_START_001 = "PROXY.START.001"
    case PROXY_STOP_001 = "PROXY.STOP.001"
    case PROXY_CLEAN_001 = "PROXY.CLEAN.001"
    case PROXY_STATE_002 = "PROXY.STATE.002"
    case PROXY_FAIL_301 = "PROXY.FAIL.301"

    // MITM
    case MITM_START_002 = "MITM.START.002"
    case MITM_STOP_001 = "MITM.STOP.001"
    case MITM_FAIL_301 = "MITM.FAIL.301"
    case MITM_FAIL_304 = "MITM.FAIL.304"
    case MITM_FAIL_306 = "MITM.FAIL.306"
    case MITM_RETRY_001 = "MITM.RETRY.001"
    case MITM_RETRY_401 = "MITM.RETRY.401"

    // Heartbeat
    case HB_FETCH_001 = "HB.FETCH.001"
    case HB_FAIL_201 = "HB.FAIL.201"
    case HB_FAIL_202 = "HB.FAIL.202"
    case HB_FAIL_203 = "HB.FAIL.203"
    case HB_STATE_202 = "HB.STATE.202"
    case HB_CMD_002 = "HB.CMD.002"

    // Network
    case NET_STATE_102 = "NET.STATE.102"
    case NET_STATE_103 = "NET.STATE.103"
    case NET_STATE_104 = "NET.STATE.104"
    case NET_FAIL_301 = "NET.FAIL.301"

    // Sync
    case SYNC_FAIL_201 = "SYNC.FAIL.201"

    // Remote State
    case STATE_STATE_001 = "STATE.STATE.001"
    case STATE_CMD_003 = "STATE.CMD.003"
    case STATE_FAIL_201 = "STATE.FAIL.201"

    // Launch
    case LAUNCH_FAIL_301 = "LAUNCH.FAIL.301"

    // App Blocking / Enforcement
    case BLOCK_APP_001 = "BLOCK.APP.001"     // App blocked and terminated
    case BLOCK_APP_002 = "BLOCK.APP.002"     // App block failed (couldn't terminate)
    case BLOCK_WARN_001 = "BLOCK.WARN.001"   // App warn shown
    case BLOCK_FLAG_001 = "BLOCK.FLAG.001"   // App flagged notification shown
    case BLOCK_REQ_001 = "BLOCK.REQ.001"     // Access request submitted

    // System Health
    case SYS_HEALTH_001 = "SYS.HEALTH.001"

    var level: LogLevel {
        switch self {
        case .MITM_RETRY_401:
            return .fatal
        case .APP_FAIL_301,
             .AUTH_FAIL_301,
             .ENROLL_FAIL_301,
             .CERT_FAIL_301, .CERT_FAIL_303,
             .PROXY_FAIL_301,
             .MITM_FAIL_301, .MITM_FAIL_304, .MITM_FAIL_306,
             .NET_FAIL_301,
             .LAUNCH_FAIL_301,
             .BLOCK_APP_002:
            return .error
        case .AUTH_AUTH_004,
             .AUTH_FAIL_201, .AUTH_FAIL_302, .AUTH_FAIL_303,
             .CERT_WARN_201,
             .PROXY_CLEAN_001,
             .MITM_RETRY_001,
             .HB_FAIL_201, .HB_FAIL_202, .HB_FAIL_203, .HB_STATE_202,
             .SYNC_FAIL_201,
             .STATE_CMD_003,
             .BLOCK_WARN_001:
            return .warning
        case .STATE_FAIL_201:
            return .debug
        default:
            return .info
        }
    }

    var action: ActionCategory {
        switch self {
        case .MITM_RETRY_401:
            return .alertOps
        case .AUTH_AUTH_004, .AUTH_FAIL_301, .CERT_FAIL_303, .ENROLL_FAIL_301, .STATE_CMD_003,
             .BLOCK_REQ_001:
            return .userAction
        case .APP_FAIL_301, .AUTH_FAIL_302, .AUTH_FAIL_303,
             .CERT_FAIL_301, .PROXY_FAIL_301,
             .MITM_FAIL_301,
             .HB_FAIL_202, .HB_STATE_202,
             .LAUNCH_FAIL_301,
             .BLOCK_APP_002:
            return .investigate
        case .MITM_FAIL_304, .MITM_FAIL_306, .MITM_RETRY_001, .AUTH_FAIL_201:
            return .autoRetry
        case .CERT_STATE_105, .PROXY_CLEAN_001:
            return .selfHealing
        case .HB_FAIL_201, .HB_FAIL_203, .SYNC_FAIL_201,
             .NET_STATE_102:
            return .monitor
        default:
            return .none
        }
    }

    var service: String {
        rawValue.components(separatedBy: ".").first?.lowercased() ?? "unknown"
    }

    var operation: String {
        let parts = rawValue.components(separatedBy: ".")
        return parts.count > 1 ? parts[1].lowercased() : "unknown"
    }

    var levelTag: String {
        switch level {
        case .debug: return "[DEBUG]"
        case .info: return "[INFO] "
        case .warning: return "[WARN] "
        case .error: return "[ERROR]"
        case .fatal: return "[FATAL]"
        }
    }

    var sentryLevel: SentryLevel {
        switch level {
        case .debug: return .debug
        case .info: return .info
        case .warning: return .warning
        case .error: return .error
        case .fatal: return .fatal
        }
    }
}
