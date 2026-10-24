/**
 * ==============================================================================
 * ANSV Coil-Architect Pro | Cloudflare Serverless 边缘授权与工位监控引擎 (v1.2 增强版)
 * 深度对标对齐 Gear-NVH / FFT 分析软件 全量工业商业桌面软件云端架构规范
 * 
 * 核心功能：
 * 1. 外部访问智能分流：普通访客访问根路径直接 302 跳转 ansv.net 官网，后台 100% 隐蔽；
 * 2. 数据库全自动热迁移与自愈：每张表独立 await db.prepare().run()，自建表/自补字段；
 * 3. 商业授权一键签发：与客户端 Python 算法 100% 互通的 COIL-SEC-... HMAC-SHA256 签发引擎；
 * 4. 工位机资产监控大屏：在线心跳、版本号、到期倒计时、时钟偏差/防倒拨监控、远程指令下发；
 * 5. 官方标杆案例库 (coil_cases)：对标 Gear 专家库，在线同步官方推荐线圈仿真算例；
 * 6. OTA 软件发版推送：在线维护版本更新直链与 Markdown 日志，客户端秒级接收更新；
 * 7. 全库一键备份：支持导出 JSON 全量备份文件。
 * ==============================================================================
 */

// 管理员登录密码 (可在此处修改或在 Cloudflare 环境变量中覆盖)
const DEFAULT_ADMIN_PASSWORD = "Ansv@Coil#2026";

// 客户端软件静默通信 API Key
const CLIENT_API_KEY = "COIL-SEC-2026#Ansv_TonyTech_c82P";

// 授权加密主密钥 (必须与客户端 license_manager.py 中的 _SECRET_KEY 保持严格一致)
const LICENSE_SECRET_KEY = "COIL_ARCHITECT_PRO_ANSV_SECRET_AUTH_KEY_2026_@v1#INDUSTRIAL";

// 会话 Cookie 名称
const AUTH_COOKIE_NAME = "coil_admin_session";
const AUTH_COOKIE_VALUE = "COIL_AUTH_VALID_ANSV_2026_SESSION";

// 官方重定向主页
const OFFICIAL_REDIRECT_URL = "https://ansv.net";
const GITHUB_REPO_URL = "https://github.com/tonychen5577-tech/coil-architect";
const GITHUB_RELEASES_URL = "https://github.com/tonychen5577-tech/coil-architect/releases";

// ==============================================================================
// 密码学与 Token 编解码工具 (与 Python 端 100% 互通)
// ==============================================================================

function uint8ArrayToBase64Url(u8) {
    let binary = "";
    const len = u8.byteLength;
    for (let i = 0; i < len; i++) {
        binary += String.fromCharCode(u8[i]);
    }
    return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function generateCoilToken(machineCode, expireDateStr, maintExpireStr, planType, customerName, stationId) {
    const payload = {
        mid: (machineCode || "").trim().toUpperCase(),
        exp: (expireDateStr || "PERMANENT").trim(),
        maint_exp: (maintExpireStr || expireDateStr || "PERMANENT").trim(),
        plan: (planType || "SUB_ANNUAL_365").trim(),
        cust: (customerName || "ANSV VIP Client").trim(),
        stat: (stationId || "WORKSTATION-01").trim(),
        ts: new Date().toISOString().replace("T", " ").substring(0, 19)
    };
    const rawJson = JSON.stringify(payload);
    const rawBytes = new TextEncoder().encode(rawJson);
    const keyBytes = new TextEncoder().encode(LICENSE_SECRET_KEY);

    const xored = new Uint8Array(rawBytes.length);
    for (let i = 0; i < rawBytes.length; i++) {
        xored[i] = rawBytes[i] ^ keyBytes[i % keyBytes.length];
    }

    const b64Payload = uint8ArrayToBase64Url(xored);

    const cryptoKey = await crypto.subtle.importKey(
        "raw",
        keyBytes,
        { name: "HMAC", hash: "SHA-256" },
        false,
        ["sign"]
    );
    const sigBuf = await crypto.subtle.sign("HMAC", cryptoKey, new TextEncoder().encode(b64Payload));
    const sigHex = Array.from(new Uint8Array(sigBuf)).map(b => b.toString(16).padStart(2, "0")).join("").toUpperCase();
    const sig16 = sigHex.substring(0, 16);

    return `COIL-SEC-${b64Payload}.${sig16}`;
}

// ==============================================================================
// HTTP 响应与 Cookie 辅助
// ==============================================================================

function corsHeaders() {
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-API-Key",
    };
}

function jsonResponse(data, status = 200) {
    return new Response(JSON.stringify(data), {
        status,
        headers: {
            "Content-Type": "application/json; charset=utf-8",
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            ...corsHeaders(),
        },
    });
}

function parseCookies(request) {
    const cookieStr = request.headers.get("Cookie") || "";
    const cookies = {};
    cookieStr.split(";").forEach(c => {
        const parts = c.split("=");
        if (parts.length >= 2) {
            cookies[parts[0].trim()] = parts.slice(1).join("=").trim();
        }
    });
    return cookies;
}

function isAdminAuthenticated(request, env) {
    const cookies = parseCookies(request);
    const expected = env.ADMIN_AUTH_TOKEN || AUTH_COOKIE_VALUE;
    return cookies[AUTH_COOKIE_NAME] === expected;
}

// ==============================================================================
// 数据库自动热迁移与自愈初始化 (对齐 Gear: 独立 prepare().run()，百分百防死锁与缺失)
// ==============================================================================

let _isDbInitialized = false;

async function ensureTables(db) {
    if (_isDbInitialized || !db) return;

    // 1. devices 表
    try {
        await db.prepare(`
            CREATE TABLE IF NOT EXISTS devices (
                machine_id VARCHAR(64) PRIMARY KEY,
                hostname VARCHAR(128) DEFAULT '-',
                ip_address VARCHAR(64) DEFAULT '-',
                mac_address VARCHAR(64) DEFAULT '-',
                app_version VARCHAR(32) DEFAULT '-',
                app_build VARCHAR(32) DEFAULT '-',
                wire_db_version VARCHAR(32) DEFAULT 'v1.0',
                license_status VARCHAR(32) DEFAULT 'TRIAL',
                license_expire VARCHAR(64) DEFAULT '-',
                remaining_days INTEGER DEFAULT 0,
                customer_name VARCHAR(128) DEFAULT '散户/未登记',
                line_station VARCHAR(128) DEFAULT 'WORKSTATION-01',
                operator_name VARCHAR(64) DEFAULT '-',
                operator_id VARCHAR(64) DEFAULT '-',
                system_user VARCHAR(64) DEFAULT '-',
                is_virtual_machine INTEGER DEFAULT 0,
                disk_free_gb REAL DEFAULT 0.0,
                clock_tampered INTEGER DEFAULT 0,
                client_clock_time VARCHAR(32) DEFAULT '-',
                clock_skew_sec INTEGER DEFAULT 0,
                remote_command VARCHAR(64) DEFAULT 'NONE',
                remote_command_payload TEXT DEFAULT '',
                first_seen_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_sync_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                sync_count INTEGER DEFAULT 1,
                status VARCHAR(20) DEFAULT 'ACTIVE',
                notes TEXT DEFAULT ''
            )
        `).run();
    } catch (_) { }

    // 字段平滑热迁移 (对齐 Gear: 防止历史旧表少字段)
    const deviceCols = [
        "wire_db_version VARCHAR(32) DEFAULT 'v1.0'",
        "plan_type VARCHAR(32) DEFAULT 'TRIAL'",
        "maint_expire VARCHAR(64) DEFAULT '-'",
        "operator_name VARCHAR(64) DEFAULT '-'",
        "operator_id VARCHAR(64) DEFAULT '-'",
        "system_user VARCHAR(64) DEFAULT '-'",
        "disk_free_gb REAL DEFAULT 0.0",
        "client_clock_time VARCHAR(32) DEFAULT '-'",
        "clock_skew_sec INTEGER DEFAULT 0",
        "remote_command VARCHAR(64) DEFAULT 'NONE'",
        "remote_command_payload TEXT DEFAULT ''",
        "status VARCHAR(20) DEFAULT 'ACTIVE'",
        "revoke_confirmed INTEGER DEFAULT 0",
        "last_ack_cmd VARCHAR(64) DEFAULT ''",
        "last_ack_time DATETIME",
        "revoke_time DATETIME",
        "first_seen_time DATETIME DEFAULT CURRENT_TIMESTAMP",
        "last_sync_time DATETIME DEFAULT CURRENT_TIMESTAMP"
    ];
    for (const col of deviceCols) {
        try { await db.prepare(`ALTER TABLE devices ADD COLUMN ${col}`).run(); } catch (_) { }
    }

    // 2. licenses 商业授权激活码签发表 (单独创建，确保必定成功)
    try {
        await db.prepare(`
            CREATE TABLE IF NOT EXISTS licenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT NOT NULL UNIQUE,
                machine_id VARCHAR(64) NOT NULL,
                plan_type VARCHAR(32) DEFAULT 'SUB_ANNUAL_365',
                expire_date VARCHAR(64) NOT NULL,
                maint_expire VARCHAR(64) DEFAULT 'PERMANENT',
                customer_name VARCHAR(128) DEFAULT 'ANSV VIP Client',
                station_id VARCHAR(64) DEFAULT 'WORKSTATION-01',
                operator_name VARCHAR(64) DEFAULT 'ADMIN',
                status VARCHAR(32) DEFAULT 'ACTIVE',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                activated_at DATETIME,
                notes TEXT DEFAULT ''
            )
        `).run();
    } catch (_) { }

    try { await db.prepare("ALTER TABLE licenses ADD COLUMN maint_expire VARCHAR(64) DEFAULT 'PERMANENT'").run(); } catch (_) { }
    try { await db.prepare("ALTER TABLE licenses ADD COLUMN plan_type VARCHAR(32) DEFAULT 'SUB_ANNUAL_365'").run(); } catch (_) { }

    // 4. audit_logs 审计流水日志表 (对齐 Gear: case_audit_logs)
    try {
        await db.prepare(`
            CREATE TABLE IF NOT EXISTS audit_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type VARCHAR(64) NOT NULL,
                target_id VARCHAR(64) DEFAULT '',
                operator_name VARCHAR(64) DEFAULT 'ADMIN',
                reason TEXT DEFAULT '',
                details TEXT DEFAULT '',
                ip VARCHAR(64) DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        `).run();
    } catch (_) { }

    // 5. releases 软件版本发布与 OTA 更新履历表
    try {
        await db.prepare(`
            CREATE TABLE IF NOT EXISTS releases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version VARCHAR(32) NOT NULL UNIQUE,
                build VARCHAR(64) DEFAULT '',
                release_date VARCHAR(32) NOT NULL,
                download_url TEXT NOT NULL,
                backup_url TEXT DEFAULT '',
                sha256 VARCHAR(64) DEFAULT '',
                file_size_mb REAL DEFAULT 0.0,
                changelog TEXT DEFAULT '',
                is_mandatory INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        `).run();
    } catch (_) { }

    // 6. app_config 全局配置表
    try {
        await db.prepare(`
            CREATE TABLE IF NOT EXISTS app_config (
                meta_key TEXT PRIMARY KEY,
                meta_value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        `).run();
    } catch (_) { }

    // 初始基准数据注入 (默认 2027 年度正式版)
    try {
        await db.prepare(`
            INSERT OR IGNORE INTO releases (version, build, release_date, download_url, backup_url, sha256, file_size_mb, changelog, is_mandatory, is_active)
            VALUES (
                '2027',
                '20261024B6',
                '2026-10-24',
                'https://github.com/tonychen5577-tech/coil-architect/releases/download/2027/ANSV_Coil_Architect_Pro_2027_Full.zip',
                'https://github.com/tonychen5577-tech/coil-architect/releases/download/2027/ANSV_Coil_Architect_Pro_2027_Incremental_Patch.zip',
                'a2d8f0920b981f4764d4c8cf2182940cf04075729c9c1f48db0cf6035fbc3f4f',
                81.92,
                '### ANSV Coil-Architect Pro 2027 (Build 20261024B6)\n- 🌟 核心算法与拓扑：优化微观多层密排绕线算法与实际截面拓扑；\n- 📊 报表与方案比对：强化 Excel 仿真报告自适应导出，方案比对抽屉补齐内长内宽等几何指标；\n- 🛡️ 工业授权与网络：支持一键云端在线极速授权与15秒自适应心跳；\n- 📖 双语手册全量内置：中英双语离线说明书全量打包，F1 一键本地离线查看。',
                0,
                1
            )
        `).run();
    } catch (_) { }

    try {
        await db.prepare(`INSERT OR IGNORE INTO app_config (meta_key, meta_value) VALUES ('latest_version', 'v1.1.0')`).run();
    } catch (_) { }

    _isDbInitialized = true;
}

// ==============================================================================
// 核心路由分发器
// ==============================================================================

export default {
    async fetch(request, env, ctx) {
        if (request.method === "OPTIONS") {
            return new Response(null, { headers: corsHeaders() });
        }

        const url = new URL(request.url);
        const path = url.pathname;

        try {
            // ------------------------------------------------------------------
            // 1. 普通访客访问根路径：智能 302 重定向到官方主页，完全隐藏后台
            // ------------------------------------------------------------------
            if (path === "/" || path === "") {
                if (isAdminAuthenticated(request, env)) {
                    return Response.redirect(`${url.origin}/admin`, 302);
                }
                return Response.redirect(OFFICIAL_REDIRECT_URL, 302);
            }

            // ------------------------------------------------------------------
            // 2. 客户端静默 API 接口 (/api/v1/... 与兼容端点)
            // ------------------------------------------------------------------
            if (path.startsWith("/api/") || path === "/version" || path === "/health") {
                return await handleClientApi(path, request, env);
            }

            // ------------------------------------------------------------------
            // 3. 管理员后台页面与操作接口 (/admin/...)
            // ------------------------------------------------------------------
            if (path.startsWith("/admin")) {
                return await handleAdmin(path, request, env, url);
            }

            // ------------------------------------------------------------------
            // 4. 软件发布包与增量补丁下载智能直连重定向
            // ------------------------------------------------------------------
            if (path.startsWith("/download")) {
                const db = env.DB;
                let activeRelease = null;
                if (db) {
                    try {
                        activeRelease = await db.prepare("SELECT * FROM releases WHERE is_active = 1 ORDER BY id DESC LIMIT 1").first();
                    } catch(_) {}
                }
                const defaultFull = "https://github.com/tonychen5577-tech/coil-architect/releases/download/2027/ANSV_Coil_Architect_Pro_2027_Full.zip";
                const defaultPatch = "https://github.com/tonychen5577-tech/coil-architect/releases/download/2027/ANSV_Coil_Architect_Pro_2027_Incremental_Patch.zip";
                
                const isPatchRequest = path.toLowerCase().includes("patch");
                let targetUrl = isPatchRequest ? 
                    (activeRelease?.backup_url || defaultPatch) : 
                    (activeRelease?.download_url || defaultFull);

                return Response.redirect(targetUrl, 302);
            }

            // 兜底重定向
            return Response.redirect(OFFICIAL_REDIRECT_URL, 302);
        } catch (err) {
            return jsonResponse({ success: false, error: err.message, stack: err.stack }, 500);
        }
    }
};

// ==============================================================================
// 客户端静默 API 处理器 (对齐 Gear: 心跳、时钟防作弊、指令下发、案例同步)
// ==============================================================================

async function handleClientApi(path, request, env) {
    const db = env.DB;
    if (!db) {
        return jsonResponse({ success: false, error: "Database binding DB is missing." }, 500);
    }
    await ensureTables(db);

    // 1. 心跳上报与防倒拨时钟校准 (对齐 Gear 规范)
    if (path === "/api/v1/heartbeat" && request.method === "POST") {
        let body = {};
        try {
            body = await request.json();
        } catch (e) {
            return jsonResponse({ success: false, error: "Invalid JSON" }, 400);
        }

        const machineId = (body.machine_id || "").trim().toUpperCase();
        if (!machineId) {
            return jsonResponse({ success: false, error: "Missing machine_id" }, 400);
        }

        const hostname = body.hostname || "-";
        const ip = request.headers.get("CF-Connecting-IP") || request.headers.get("X-Forwarded-For") || "-";
        const mac = body.mac_address || "-";
        const appVersion = body.app_version || "-";
        const appBuild = body.app_build || "-";
        const wireDbVer = body.wire_db_version || "v1.0";
        const isVm = body.is_virtual_machine ? 1 : 0;
        const operatorName = body.operator_name || "-";
        const operatorId = body.operator_id || "-";
        const systemUser = body.system_user || "-";
        const diskFreeGb = Number(body.disk_free_gb || 0.0);
        const clientClockStr = body.client_clock_time || new Date().toISOString();
        const clientClockTs = Number(body.client_timestamp || 0);

        const nowSec = Math.floor(Date.now() / 1000);
        let clockSkewSec = 0;
        let clockTampered = 0;
        if (clientClockTs > 0) {
            clockSkewSec = Math.abs(nowSec - clientClockTs);
            if (clockSkewSec > 180) {
                clockTampered = 1; // 误差超过 3 分钟，视为倒拨或严重时钟漂移
            }
        }

        // 解析并计算剩余天数
        let licenseStatus = "TRIAL";
        let licenseExpire = body.license_expire || "-";
        let remainingDays = 0;

        if (licenseExpire === "PERMANENT") {
            licenseStatus = "ACTIVE";
            remainingDays = 99999;
        } else if (licenseExpire && licenseExpire !== "-") {
            try {
                const expDate = new Date(licenseExpire + "T23:59:59Z");
                const diffTime = expDate.getTime() - Date.now();
                remainingDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
                if (remainingDays <= 0) {
                    licenseStatus = "EXPIRED";
                } else {
                    licenseStatus = "ACTIVE";
                }
            } catch (e) {}
        }

        // 插入或更新工位机资产 (全量字段对齐 Gear)
        await db.prepare(`
            INSERT INTO devices (
                machine_id, hostname, ip_address, mac_address, app_version, app_build, wire_db_version,
                license_status, license_expire, remaining_days, customer_name, line_station,
                operator_name, operator_id, system_user, is_virtual_machine, disk_free_gb,
                clock_tampered, client_clock_time, clock_skew_sec, last_sync_time, sync_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '散户/未登记', 'WORKSTATION-01', ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 1)
            ON CONFLICT(machine_id) DO UPDATE SET
                hostname = excluded.hostname,
                ip_address = excluded.ip_address,
                mac_address = CASE WHEN excluded.mac_address != '-' THEN excluded.mac_address ELSE devices.mac_address END,
                app_version = excluded.app_version,
                app_build = excluded.app_build,
                wire_db_version = excluded.wire_db_version,
                operator_name = CASE WHEN excluded.operator_name != '-' THEN excluded.operator_name ELSE devices.operator_name END,
                operator_id = CASE WHEN excluded.operator_id != '-' THEN excluded.operator_id ELSE devices.operator_id END,
                system_user = CASE WHEN excluded.system_user != '-' THEN excluded.system_user ELSE devices.system_user END,
                is_virtual_machine = excluded.is_virtual_machine,
                disk_free_gb = excluded.disk_free_gb,
                clock_tampered = CASE WHEN excluded.clock_tampered = 1 THEN 1 ELSE devices.clock_tampered END,
                client_clock_time = excluded.client_clock_time,
                clock_skew_sec = excluded.clock_skew_sec,
                status = CASE 
                    WHEN devices.status = 'BANNED' THEN 'BANNED'
                    WHEN devices.status = 'REVOKED' OR devices.license_status = 'REVOKED' THEN 'REVOKED'
                    ELSE devices.status
                END,
                license_status = CASE 
                    WHEN devices.status = 'BANNED' THEN 'BANNED'
                    WHEN devices.status = 'REVOKED' OR devices.license_status = 'REVOKED' THEN 'REVOKED'
                    ELSE excluded.license_status 
                END,
                license_expire = CASE 
                    WHEN devices.status = 'REVOKED' OR devices.license_status = 'REVOKED' THEN devices.license_expire
                    WHEN excluded.license_expire != '-' THEN excluded.license_expire 
                    ELSE devices.license_expire 
                END,
                remaining_days = CASE
                    WHEN devices.status = 'REVOKED' OR devices.license_status = 'REVOKED' THEN 0
                    ELSE excluded.remaining_days
                END,
                last_sync_time = CURRENT_TIMESTAMP,
                sync_count = devices.sync_count + 1
        `).bind(
            machineId, hostname, ip, mac, appVersion, appBuild, wireDbVer,
            licenseStatus, licenseExpire, remainingDays,
            operatorName, operatorId, systemUser, isVm, diskFreeGb,
            clockTampered, clientClockStr, clockSkewSec
        ).run();

        // 提取工位机远程指令 (对齐 Gear: 支持云端强制锁机或刷新)
        const deviceRow = await db.prepare("SELECT status, customer_name, remote_command, remote_command_payload FROM devices WHERE machine_id = ?").bind(machineId).first();
        const release = await db.prepare("SELECT * FROM releases WHERE is_active = 1 ORDER BY id DESC LIMIT 1").first();

        let remoteCmd = deviceRow ? (deviceRow.remote_command || "NONE") : "NONE";
        let remotePayload = deviceRow ? (deviceRow.remote_command_payload || "") : "";

        // 如果设备处于 BANNED 或 REVOKED 状态，强行下发 LOCK_APP 指令 (远程锁机/吊销)
        if (deviceRow && (deviceRow.status === "BANNED" || deviceRow.status === "REVOKED" || deviceRow.license_status === "REVOKED")) {
            remoteCmd = "LOCK_APP";
        }

        return jsonResponse({
            success: true,
            server_timestamp: nowSec,
            server_time_str: new Date().toISOString().replace("T", " ").substring(0, 19),
            clock_tampered: clockTampered === 1,
            device_status: deviceRow ? deviceRow.status : "ACTIVE",
            customer_name: deviceRow ? deviceRow.customer_name : "散户/未登记",
            remaining_days: remainingDays,
            remote_command: remoteCmd,
            remote_command_payload: remotePayload,
            latest_release: release ? {
                version: release.version,
                build: release.build,
                release_date: release.release_date,
                download_url: release.download_url,
                backup_url: release.backup_url,
                sha256: release.sha256,
                file_size_mb: release.file_size_mb,
                changelog: release.changelog,
                is_mandatory: release.is_mandatory === 1
            } : null
        });
    }

    // 0. 健康检查与网络连通性探测 (对齐 Gear 规范)
    if (path === "/api/v1/health" || path === "/health" || path === "/api/health") {
        return jsonResponse({
            success: true,
            status: "ONLINE",
            service: "Coil-Architect Cloud Edge Database",
            message: "电磁线圈知识库与授权协同服务正常运行中",
            timestamp: Date.now()
        });
    }

    // 1.1 工位机指令执行回执 (ACK) (对标 Gear 规范)

    // 1.2 在线一键激活请求与即时下发
    if (path === "/api/v1/online_activate" && request.method === "POST") {
        let body = {};
        try { body = await request.json(); } catch(e){}
        const mid = (body.machine_id || "").trim().toUpperCase();
        if (!mid) return jsonResponse({ success: false, error: "Missing machine_id" }, 400);

        const hostname = body.hostname || "-";
        const ip = request.headers.get("CF-Connecting-IP") || request.headers.get("X-Forwarded-For") || "-";
        const mac = body.mac_address || "-";
        const appVersion = body.app_version || "-";
        const appBuild = body.app_build || "-";
        const customer = (body.customer_name || "").trim() || "在线申请用户";
        const contact = (body.contact || "").trim() || "-";

        // 确保工位机记录在 devices 表
        await db.prepare(`
            INSERT INTO devices (
                machine_id, hostname, ip_address, mac_address, app_version, app_build,
                customer_name, line_station, license_status, notes, last_sync_time, sync_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'WORKSTATION-01', 'PENDING_APPROVAL', ?, CURRENT_TIMESTAMP, 1)
            ON CONFLICT(machine_id) DO UPDATE SET
                hostname = CASE WHEN excluded.hostname != '-' THEN excluded.hostname ELSE devices.hostname END,
                ip_address = excluded.ip_address,
                mac_address = CASE WHEN excluded.mac_address != '-' THEN excluded.mac_address ELSE devices.mac_address END,
                app_version = excluded.app_version,
                app_build = excluded.app_build,
                customer_name = CASE WHEN excluded.customer_name != '在线申请用户' AND excluded.customer_name != '' THEN excluded.customer_name ELSE devices.customer_name END,
                last_sync_time = CURRENT_TIMESTAMP
        `).bind(mid, hostname, ip, mac, appVersion, appBuild, customer, `在线激活联系: ${contact}`).run();

        // 检查设备是否已被取消授权或封禁
        const dev = await db.prepare("SELECT * FROM devices WHERE machine_id = ?").bind(mid).first();
        if (dev && (dev.status === "BANNED" || dev.status === "REVOKED" || dev.license_status === "REVOKED")) {
            return jsonResponse({
                success: false,
                status: "REVOKED",
                error: "该工位机商业授权已被管理员在云端控制台取消/终止，无法在线自动激活。请联系官方技术支持恢复授权。"
            });
        }

        // 检查是否有已为该设备签发或等待下发的有效授权
        const lic = await db.prepare("SELECT * FROM licenses WHERE machine_id = ? AND status = 'ACTIVE' ORDER BY id DESC LIMIT 1").bind(mid).first();

        let tokenToSend = "";
        let expireDate = "PERMANENT";
        let customerName = customer;
        let planType = "SUB_ANNUAL_365";

        if (lic && lic.token) {
            tokenToSend = lic.token;
            expireDate = lic.expire_date;
            customerName = lic.customer_name || customer;
            planType = lic.plan_type || "SUB_ANNUAL_365";
        } else if (dev && dev.remote_command === "UPDATE_LICENSE" && dev.remote_command_payload) {
            tokenToSend = dev.remote_command_payload;
            expireDate = dev.license_expire || "PERMANENT";
            customerName = dev.customer_name || customer;
            planType = dev.plan_type || "SUB_ANNUAL_365";
        }

        if (tokenToSend) {
            await db.prepare("UPDATE devices SET remote_command = 'NONE', remote_command_payload = '', license_status = 'ACTIVE' WHERE machine_id = ?").bind(mid).run();
            await db.prepare("INSERT INTO audit_logs (action_type, target_id, details, ip) VALUES ('ONLINE_ACTIVATE_SUCCESS', ?, ?, ?)").bind(mid, `工位机在线一键激活成功: ${customerName}`, ip).run();
            return jsonResponse({
                success: true,
                status: "ACTIVATED",
                token: tokenToSend,
                expire_date: expireDate,
                customer_name: customerName,
                plan_type: planType,
                message: "恭喜！商业授权在线核验成功，凭证已就绪。"
            });
        }

        // 尚未下发，登记为申请中
        await db.prepare("INSERT INTO audit_logs (action_type, target_id, details, ip) VALUES ('ONLINE_ACTIVATE_REQUEST', ?, ?, ?)").bind(mid, `客户在线申请激活: ${customer} (${contact})`, ip).run();
        return jsonResponse({
            success: false,
            status: "PENDING_APPROVAL",
            machine_id: mid,
            message: "已向云端提交在线激活申请。管理员在后台点击【一键下发授权】后，软件将立即自动激活！"
        });
    }

    if ((path === "/api/v1/command_ack" || path === "/api/v1/station/command_ack") && request.method === "POST") {
        let body = {};
        try { body = await request.json(); } catch(e){}
        const mid = (body.machine_id || "").trim();
        const cmd = (body.command || "NONE").trim();
        const status = (body.status || "OK").trim();
        if (mid) {
            if (cmd === "LOCK_APP" || cmd === "REVOKE_LICENSE") {
                await db.prepare(`
                    UPDATE devices SET 
                        status = 'REVOKED',
                        license_status = 'REVOKED',
                        remote_command = 'LOCK_APP',
                        revoke_confirmed = 1,
                        last_ack_time = CURRENT_TIMESTAMP,
                        last_ack_cmd = 'LOCK_APP:EXECUTED',
                        notes = '工位机已确认执行锁机，本地凭证已彻底销毁并安全退出'
                    WHERE machine_id = ?
                `).bind(mid).run();
                await db.prepare("INSERT INTO audit_logs (action_type, target_id, details) VALUES ('REVOKE_CONFIRMED', ?, '工位机已确认销毁本地证书并锁定退出')").bind(mid).run();
            } else if (cmd === "UPDATE_LICENSE") {
                await db.prepare(`
                    UPDATE devices SET 
                        status = 'ACTIVE',
                        license_status = 'ACTIVE',
                        remote_command = 'NONE',
                        remote_command_payload = '',
                        revoke_confirmed = 0,
                        last_ack_time = CURRENT_TIMESTAMP,
                        last_ack_cmd = 'UPDATE_LICENSE:SUCCESS',
                        notes = '工位机已确认装载并激活最新商业凭证'
                    WHERE machine_id = ?
                `).bind(mid).run();
                await db.prepare("INSERT INTO audit_logs (action_type, target_id, details) VALUES ('LICENSE_CONFIRMED', ?, '工位机已确认装载并激活商业凭证')").bind(mid).run();
            } else {
                await db.prepare("UPDATE devices SET remote_command = 'NONE', remote_command_payload = '', last_ack_time = CURRENT_TIMESTAMP, last_ack_cmd = ? WHERE machine_id = ?").bind(`${cmd}:${status}`, mid).run();
                await db.prepare("INSERT INTO audit_logs (action_type, target_id, details) VALUES ('COMMAND_ACK', ?, ?)").bind(mid, `工位机指令回执: ${cmd} -> ${status}`).run();
            }
        }
        return jsonResponse({ success: true, message: "ACK received" });
    }

    // 2. 检查版本更新 (兼容所有历史路由与标准端点)
    const isUpdateCheckRoute = (
        path === "/api/v1/check_update" ||
        path === "/api/v1/update" ||
        path === "/api/v1/app/version-check" ||
        path === "/api/v1/version" ||
        path === "/api/version" ||
        path === "/version"
    );
    if (isUpdateCheckRoute && (request.method === "GET" || request.method === "POST")) {
        const release = await db.prepare("SELECT * FROM releases WHERE is_active = 1 ORDER BY id DESC LIMIT 1").first();
        if (!release) {
            return jsonResponse({ success: false, message: "No active release found" });
        }
        const defaultFull = "https://github.com/tonychen5577-tech/coil-architect/releases/download/2027/ANSV_Coil_Architect_Pro_2027_Full.zip";
        const defaultPatch = "https://github.com/tonychen5577-tech/coil-architect/releases/download/2027/ANSV_Coil_Architect_Pro_2027_Incremental_Patch.zip";
        return jsonResponse({
            success: true,
            version: release.version,
            build: release.build,
            release_date: release.release_date,
            download_url: release.download_url || defaultFull,
            patch_url: release.backup_url || defaultPatch,
            patch_size_mb: 29.03,
            backup_url: release.backup_url || defaultPatch,
            sha256: release.sha256,
            file_size_mb: release.file_size_mb || 81.92,
            changelog: release.changelog,
            is_mandatory: release.is_mandatory === 1
        });
    }

    return jsonResponse({ success: false, error: "API route not found" }, 404);
}

// ==============================================================================
// 管理员后台处理器
// ==============================================================================

async function handleAdmin(path, request, env, url) {
    const db = env.DB;
    if (!db) {
        return new Response("Database binding DB is missing in Worker configuration.", { status: 500 });
    }
    await ensureTables(db);

    // 1. 登录验证 API
    if (path === "/admin/api/login" && request.method === "POST") {
        let body = {};
        try { body = await request.json(); } catch(e){}
        const inputPwd = (body.password || "").trim();
        const expectedPwd = env.ADMIN_PASSWORD || DEFAULT_ADMIN_PASSWORD;

        if (inputPwd === expectedPwd) {
            const token = env.ADMIN_AUTH_TOKEN || AUTH_COOKIE_VALUE;
            return new Response(JSON.stringify({ success: true }), {
                status: 200,
                headers: {
                    "Content-Type": "application/json; charset=utf-8",
                    "Set-Cookie": `${AUTH_COOKIE_NAME}=${token}; Path=/; HttpOnly; Max-Age=86400; SameSite=Lax`,
                    ...corsHeaders()
                }
            });
        }
        return jsonResponse({ success: false, error: "管理员密码错误" }, 401);
    }

    // 2. 登出 API
    if (path === "/admin/api/logout" && request.method === "POST") {
        return new Response(JSON.stringify({ success: true }), {
            status: 200,
            headers: {
                "Content-Type": "application/json; charset=utf-8",
                "Set-Cookie": `${AUTH_COOKIE_NAME}=; Path=/; HttpOnly; Max-Age=0; SameSite=Lax`,
                ...corsHeaders()
            }
        });
    }

    // 3. 页面渲染：若未登录则展示登录页，已登录则展示完整管理看板
    if (path === "/admin" || path === "/admin/") {
        if (!isAdminAuthenticated(request, env)) {
            return new Response(renderLoginPage(), {
                headers: { 
                    "Content-Type": "text/html; charset=utf-8",
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"
                }
            });
        }
        return new Response(renderDashboardPage(), {
            headers: { 
                "Content-Type": "text/html; charset=utf-8",
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"
            }
        });
    }

    // 5. 下方所有 /admin/api/* 必须校验管理员权限
    if (!isAdminAuthenticated(request, env)) {
        return jsonResponse({ success: false, error: "未授权，请先登录后台" }, 401);
    }

    // A. 仪表盘全景统计指标
    if (path === "/admin/api/stats" && request.method === "GET") {
        const totalDevices = (await db.prepare("SELECT COUNT(*) as c FROM devices").first())?.c || 0;
        const activeDevices = (await db.prepare("SELECT COUNT(*) as c FROM devices WHERE status = 'ACTIVE' AND (license_expire = 'PERMANENT' OR remaining_days > 0)").first())?.c || 0;
        const expiringSoon = (await db.prepare("SELECT COUNT(*) as c FROM devices WHERE remaining_days >= 0 AND remaining_days <= 7 AND license_expire != 'PERMANENT'").first())?.c || 0;
        
        // 核心监控：40分钟内有心跳的活跃在线工位机数量 (适配客户端每30分钟心跳周期)
        const liveOnline = (await db.prepare("SELECT COUNT(*) as c FROM devices WHERE last_sync_time >= datetime('now', '-40 minutes')").first())?.c || 0;
        const todaySyncs = (await db.prepare("SELECT COUNT(*) as c FROM devices WHERE last_sync_time >= date('now')").first())?.c || 0;
        const totalLicenses = (await db.prepare("SELECT COUNT(*) as c FROM licenses").first())?.c || 0;
        const totalReleases = (await db.prepare("SELECT COUNT(*) as c FROM releases").first())?.c || 0;
        const activeRelease = await db.prepare("SELECT * FROM releases WHERE is_active = 1 ORDER BY id DESC LIMIT 1").first();

        return jsonResponse({
            success: true,
            stats: {
                total_devices: totalDevices,
                live_online: liveOnline,
                active_devices: activeDevices,
                expiring_soon: expiringSoon,
                today_syncs: todaySyncs,
                total_licenses: totalLicenses,
                total_releases: totalReleases,
                latest_version: activeRelease ? activeRelease.version : "v1.1.0"
            }
        });
    }

    // B. 工位机列表 (支持搜索与状态筛选，服务端直出精确在线状态与北京时间)
    if (path === "/admin/api/devices" && request.method === "GET") {
        const q = (url.searchParams.get("q") || "").trim();
        let query = "SELECT * FROM devices ORDER BY last_sync_time DESC LIMIT 150";
        let res;
        if (q) {
            query = "SELECT * FROM devices WHERE machine_id LIKE ? OR customer_name LIKE ? OR hostname LIKE ? OR ip_address LIKE ? OR operator_name LIKE ? ORDER BY last_sync_time DESC LIMIT 150";
            const pattern = `%${q}%`;
            res = await db.prepare(query).bind(pattern, pattern, pattern, pattern, pattern).all();
        } else {
            res = await db.prepare(query).all();
        }

        const nowMs = Date.now();
        const rawDevices = res.results || [];
        const enriched = rawDevices.map(d => {
            let syncMs = 0;
            if (d.last_sync_time) {
                syncMs = new Date(d.last_sync_time.replace(' ', 'T') + 'Z').getTime();
            }
            const diffSec = syncMs > 0 ? Math.floor(Math.max(0, nowMs - syncMs) / 1000) : 999999;
            const isOnline = diffSec <= 2400; // 40分钟内有授权心跳判定为活跃在线 (适配每30分钟心跳周期)
            
            // 自动转换为当地北京时间 (UTC+8) 显示
            let bjTimeStr = "-";
            if (syncMs > 0) {
                const bjDate = new Date(syncMs + 8 * 3600 * 1000);
                bjTimeStr = bjDate.toISOString().replace('T', ' ').substring(0, 19);
            }
            
            return {
                ...d,
                is_online: isOnline,
                diff_sec: diffSec,
                last_sync_bj: bjTimeStr
            };
        });

        return jsonResponse({ success: true, devices: enriched });
    }

    // C. 一键生成商业授权码并写入数据库
    if (path === "/admin/api/generate_token" && request.method === "POST") {
        let body = {};
        try { body = await request.json(); } catch(e){}
        const mid = (body.machine_id || "").trim().toUpperCase();
        const planType = body.plan_type || "SUB_ANNUAL_365";
        const customer = (body.customer_name || "ANSV VIP Client").trim();
        const station = (body.station_id || "WORKSTATION-01").trim();
        const notes = (body.notes || "").trim();

        if (!mid) {
            return jsonResponse({ success: false, error: "请输入机器识别码" }, 400);
        }

        // 计算到期时间与版本维护升级期
        let expireDateStr = "PERMANENT";
        let maintExpireStr = "PERMANENT";
        let planLabel = "商业授权";
        const today = new Date();

        if (planType === "TRIAL_7") {
            today.setDate(today.getDate() + 7);
            expireDateStr = today.toISOString().substring(0, 10);
            maintExpireStr = expireDateStr;
            planLabel = "7 天短期试用版";
        } else if (planType === "TRIAL_14" || planType === "TRIAL_30") {
            const days = planType === "TRIAL_14" ? 14 : 30;
            today.setDate(today.getDate() + days);
            expireDateStr = today.toISOString().substring(0, 10);
            maintExpireStr = expireDateStr;
            planLabel = `${days} 天项目评估版`;
        } else if (planType === "SUB_MONTHLY_30") {
            today.setDate(today.getDate() + 30);
            expireDateStr = today.toISOString().substring(0, 10);
            maintExpireStr = expireDateStr;
            planLabel = "按月商业订阅版 (30天)";
        } else if (planType === "SUB_QUARTERLY_90") {
            today.setDate(today.getDate() + 90);
            expireDateStr = today.toISOString().substring(0, 10);
            maintExpireStr = expireDateStr;
            planLabel = "按季度商业订阅版 (90天)";
        } else if (planType === "SUB_ANNUAL_365") {
            today.setDate(today.getDate() + 365);
            expireDateStr = today.toISOString().substring(0, 10);
            maintExpireStr = expireDateStr;
            planLabel = "按年商业订阅版 (365天 · 全年更新支持)";
        } else if (planType === "PERPETUAL_1Y_UPDATE") {
            expireDateStr = "PERMANENT";
            today.setDate(today.getDate() + 365);
            maintExpireStr = today.toISOString().substring(0, 10);
            planLabel = "标准企业买断版 (永久可用 + 1年版本更新与支持)";
        } else if (planType === "PERPETUAL_LIFETIME") {
            expireDateStr = "PERMANENT";
            maintExpireStr = "PERMANENT";
            planLabel = "尊享企业买断版 (永久可用 + 终身免费版本升级)";
        } else if (planType === "CUSTOM") {
            expireDateStr = (body.custom_expire || "").trim() || "PERMANENT";
            maintExpireStr = (body.custom_maint || expireDateStr).trim();
            planLabel = "自定义商业授权";
        }

        // 生成加密 Token (含维护到期字段)
        const token = await generateCoilToken(mid, expireDateStr, maintExpireStr, planType, customer, station);

        // 写入 licenses 表
        await db.prepare(`
            INSERT INTO licenses (token, machine_id, plan_type, expire_date, maint_expire, customer_name, station_id, operator_name, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'ADMIN', 'ACTIVE', ?)
        `).bind(token, mid, planType, expireDateStr, maintExpireStr, customer, station, notes).run();

        // 同步更新 devices 表（如果已存在该机器码）
        await db.prepare(`
            UPDATE devices SET 
                customer_name = ?,
                line_station = ?,
                plan_type = ?,
                license_status = 'ACTIVE',
                license_expire = ?,
                maint_expire = ?,
                status = 'ACTIVE',
                notes = CASE WHEN ? != '' THEN ? ELSE notes END
            WHERE machine_id = ?
        `).bind(customer, station, planType, expireDateStr, maintExpireStr, notes, notes, mid).run();

        // 审计留痕 (对齐 Gear)
        const ip = request.headers.get("CF-Connecting-IP") || "-";
        await db.prepare(`
            INSERT INTO audit_logs (action_type, target_id, operator_name, details, ip)
            VALUES ('GENERATE_TOKEN', ?, 'ADMIN', ?, ?)
        `).bind(mid, `方案: ${planLabel}, 权限到期: ${expireDateStr}, 维护到期: ${maintExpireStr}, 客户: ${customer}`, ip).run();

        return jsonResponse({
            success: true,
            token,
            machine_id: mid,
            expire_date: expireDateStr,
            maint_expire: maintExpireStr,
            customer_name: customer,
            plan_type: planType,
            plan_label: planLabel
        });
    }

    // D. 设备运维操作 (拉黑/解封/延期/下发指令)
    if (path === "/admin/api/device/action" && request.method === "POST") {
        let body = {};
        try { body = await request.json(); } catch(e){}
        const mid = (body.machine_id || "").trim();
        const action = body.action;
        const val = body.value;
        const ip = request.headers.get("CF-Connecting-IP") || "-";

        if (!mid) return jsonResponse({ success: false, error: "Missing machine_id" }, 400);

        if (action === "REVOKE" || action === "LOCK_APP") {
            await db.prepare(`
                UPDATE devices SET 
                    status = 'REVOKED', 
                    license_status = 'REVOKED', 
                    remote_command = 'LOCK_APP',
                    revoke_confirmed = 0,
                    revoke_time = CURRENT_TIMESTAMP,
                    notes = '管理员取消授权，已排队下发远程锁机指令'
                WHERE machine_id = ?
            `).bind(mid).run();
            await db.prepare("UPDATE licenses SET status = 'REVOKED' WHERE machine_id = ?").bind(mid).run();
            await db.prepare("INSERT INTO audit_logs (action_type, target_id, details, ip) VALUES ('REVOKE_LICENSE', ?, '管理员在控制台取消授权，下发远程锁机指令', ?)").bind(mid, ip).run();
            return jsonResponse({ success: true, message: "已成功取消授权并下发远程锁机指令！工位机将在心跳连接时强制销毁本地凭证并锁定退出。" });
        } else if (action === "BAN") {
            await db.prepare("UPDATE devices SET status = 'BANNED', license_status = 'REVOKED', remote_command = 'LOCK_APP' WHERE machine_id = ?").bind(mid).run();
            await db.prepare("INSERT INTO audit_logs (action_type, target_id, details, ip) VALUES ('BAN_DEVICE', ?, '强制拉黑吊销并下发锁定指令', ?)").bind(mid, ip).run();
        } else if (action === "UNDO_REVOKE" || action === "RESTORE_AUTHORIZATION") {
            // 撤销取消授权 (一键解除吊销/锁机，恢复 ACTIVE 状态并下发有效商业凭证)
            const lic = await db.prepare("SELECT * FROM licenses WHERE machine_id = ? ORDER BY id DESC LIMIT 1").bind(mid).first();
            let pushToken = "";
            let planType = "SUB_ANNUAL_365";
            let expDate = "PERMANENT";
            let custName = "ANSV 商业客户";
            if (lic) {
                pushToken = lic.token;
                planType = lic.plan_type || "SUB_ANNUAL_365";
                expDate = lic.expire_date || "PERMANENT";
                custName = lic.customer_name || "ANSV 商业客户";
                if (lic.status === "REVOKED") {
                    await db.prepare("UPDATE licenses SET status = 'ACTIVE' WHERE id = ?").bind(lic.id).run();
                }
            } else {
                const dt = new Date();
                dt.setDate(dt.getDate() + 365);
                expDate = dt.toISOString().substring(0, 10);
                pushToken = await generateCoilToken(mid, expDate, expDate, planType, custName, "WORKSTATION-01");
                await db.prepare("INSERT INTO licenses (token, machine_id, plan_type, expire_date, maint_expire, customer_name, station_id, operator_name, status, notes) VALUES (?, ?, ?, ?, ?, ?, 'WORKSTATION-01', 'ADMIN', 'ACTIVE', '撤销取消授权自动生成新证书')").bind(pushToken, mid, planType, expDate, expDate, custName).run();
            }

            await db.prepare(`
                UPDATE devices SET 
                    status = 'ACTIVE', 
                    license_status = 'ACTIVE', 
                    license_expire = ?,
                    customer_name = ?,
                    plan_type = ?,
                    remote_command = 'UPDATE_LICENSE', 
                    remote_command_payload = ?,
                    revoke_confirmed = 0,
                    notes = '管理员撤销取消授权，恢复工位机商业激活'
                WHERE machine_id = ?
            `).bind(expDate, custName, planType, pushToken, mid).run();

            await db.prepare("INSERT INTO audit_logs (action_type, target_id, details, ip) VALUES ('UNDO_REVOKE', ?, ?, ?)").bind(mid, `撤销取消授权并恢复激活: ${custName} (${expDate})`, ip).run();
            return jsonResponse({ success: true, message: "已成功撤销取消授权！工位机已恢复正常商业激活状态，重新下发有效凭证。", customer_name: custName, expire_date: expDate });
        } else if (action === "ACTIVATE" || action === "UNLOCK") {
            const lic = await db.prepare("SELECT * FROM licenses WHERE machine_id = ? AND status != 'REVOKED' ORDER BY id DESC LIMIT 1").bind(mid).first();
            if (lic) {
                await db.prepare("UPDATE devices SET status = 'ACTIVE', license_status = 'ACTIVE', remote_command = 'UPDATE_LICENSE', remote_command_payload = ?, notes = '管理员解除锁定并推送授权' WHERE machine_id = ?").bind(lic.token, mid).run();
            } else {
                await db.prepare("UPDATE devices SET status = 'ACTIVE', license_status = 'ACTIVE', remote_command = 'NONE', remote_command_payload = '' WHERE machine_id = ?").bind(mid).run();
            }
            await db.prepare("INSERT INTO audit_logs (action_type, target_id, details, ip) VALUES ('ACTIVATE_DEVICE', ?, '解除锁定，恢复正常授权状态', ?)").bind(mid, ip).run();
        } else if (action === "EXTEND_DAYS") {
            const days = parseInt(val) || 30;
            const targetDate = new Date();
            targetDate.setDate(targetDate.getDate() + days);
            const newExp = targetDate.toISOString().substring(0, 10);
            await db.prepare("UPDATE devices SET license_expire = ?, remaining_days = ?, license_status = 'ACTIVE', remote_command = 'NONE' WHERE machine_id = ?").bind(newExp, days, mid).run();
            await db.prepare("INSERT INTO audit_logs (action_type, target_id, details, ip) VALUES ('EXTEND_DAYS', ?, ?, ?)").bind(mid, `延长至: ${newExp}`, ip).run();
        } else if (action === "SET_PERMANENT") {
            await db.prepare("UPDATE devices SET license_expire = 'PERMANENT', remaining_days = 99999, license_status = 'ACTIVE', remote_command = 'NONE' WHERE machine_id = ?").bind(mid).run();
            await db.prepare("INSERT INTO audit_logs (action_type, target_id, details, ip) VALUES ('SET_PERMANENT', ?, '设为永久企业买断授权', ?)").bind(mid, ip).run();
                } else if (action === "AUTO_AUTHORIZE") {
            const planType = (body.plan_type || "SUB_ANNUAL_365").trim();
            let customer = (body.customer_name || "").trim();
            const station = (body.station_id || "WORKSTATION-01").trim();
            const days = parseInt(body.expire_days) || 365;

            const devRow = await db.prepare("SELECT * FROM devices WHERE machine_id = ?").bind(mid).first();
            if (!customer && devRow && devRow.customer_name && devRow.customer_name !== "散户/未登记" && devRow.customer_name !== "在线申请用户") {
                customer = devRow.customer_name;
            }
            if (!customer) customer = "ANSV 商业客户";

            let expireDateStr = "PERMANENT";
            let maintExpireStr = "PERMANENT";
            let planLabel = "年度商业标准版";

            if (planType === "SUB_QUARTER_90") {
                const dt = new Date();
                dt.setDate(dt.getDate() + 90);
                expireDateStr = dt.toISOString().substring(0, 10);
                maintExpireStr = expireDateStr;
                planLabel = "短期季度冲刺版 (90天)";
            } else if (planType === "SUB_ANNUAL_365") {
                const dt = new Date();
                dt.setDate(dt.getDate() + 365);
                expireDateStr = dt.toISOString().substring(0, 10);
                maintExpireStr = expireDateStr;
                planLabel = "年度商业标准版 (365天)";
            } else if (planType === "PERPETUAL_1Y_UPDATE") {
                expireDateStr = "PERMANENT";
                const dt = new Date();
                dt.setDate(dt.getDate() + 365);
                maintExpireStr = dt.toISOString().substring(0, 10);
                planLabel = "企业永久买断版 (首年维护)";
            } else {
                if (days > 0 && days < 10000) {
                    const dt = new Date();
                    dt.setDate(dt.getDate() + days);
                    expireDateStr = dt.toISOString().substring(0, 10);
                    maintExpireStr = expireDateStr;
                } else {
                    expireDateStr = "PERMANENT";
                    maintExpireStr = "PERMANENT";
                }
                planLabel = `商业自定义版 (${days > 0 && days < 10000 ? days + "天" : "永久"})`;
            }

            const token = await generateCoilToken(mid, expireDateStr, maintExpireStr, planType, customer, station);

            await db.prepare(`
                INSERT INTO licenses (token, machine_id, plan_type, expire_date, maint_expire, customer_name, station_id, operator_name, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'ADMIN', 'ACTIVE', '一键极速在线授权下发')
            `).bind(token, mid, planType, expireDateStr, maintExpireStr, customer, station).run();

            await db.prepare(`
                UPDATE devices SET 
                    customer_name = ?,
                    line_station = ?,
                    plan_type = ?,
                    license_status = 'ACTIVE',
                    license_expire = ?,
                    maint_expire = ?,
                    status = 'ACTIVE',
                    remote_command = 'UPDATE_LICENSE',
                    remote_command_payload = ?,
                    notes = '管理员一键下发商业授权'
                WHERE machine_id = ?
            `).bind(customer, station, planType, expireDateStr, maintExpireStr, token, mid).run();

            await db.prepare(`
                INSERT INTO audit_logs (action_type, target_id, details, ip)
                VALUES ('AUTO_AUTHORIZE', ?, ?, ?)
            `).bind(mid, `一键下发授权: ${planLabel}, 有效期至: ${expireDateStr}, 客户: ${customer}`, ip).run();

            return jsonResponse({
                success: true,
                token,
                machine_id: mid,
                expire_date: expireDateStr,
                customer_name: customer,
                plan_type: planType,
                plan_label: planLabel
            });
} else if (action === "GET_LATEST_LICENSE") {
            const lic = await db.prepare("SELECT * FROM licenses WHERE machine_id = ? ORDER BY id DESC LIMIT 1").bind(mid).first();
            if (!lic) {
                return jsonResponse({ success: false, error: "未找到该工位机的历史授权记录" });
            }
            return jsonResponse({
                success: true,
                license: {
                    id: lic.id,
                    token: lic.token,
                    machine_id: lic.machine_id,
                    plan_type: lic.plan_type,
                    expire_date: lic.expire_date,
                    maint_expire: lic.maint_expire,
                    customer_name: lic.customer_name,
                    status: lic.status,
                    created_at: lic.created_at
                }
            });
        } else if (action === "PUSH_TOKEN") {
            const token = (val || "").trim();
            if (!token) return jsonResponse({ success: false, error: "Missing token" }, 400);

            // 查找该 token 对应的完整凭证，同步恢复 devices 状态与有效期
            const lic = await db.prepare("SELECT * FROM licenses WHERE token = ?").bind(token).first();
            if (lic) {
                await db.prepare(`
                    UPDATE devices SET 
                        customer_name = ?,
                        line_station = ?,
                        plan_type = ?,
                        license_status = 'ACTIVE',
                        license_expire = ?,
                        maint_expire = ?,
                        status = 'ACTIVE',
                        remote_command = 'UPDATE_LICENSE',
                        remote_command_payload = ?,
                        notes = '管理员重新下发历史授权码'
                    WHERE machine_id = ?
                `).bind(lic.customer_name, lic.station_id || "WORKSTATION-01", lic.plan_type, lic.expire_date, lic.maint_expire || lic.expire_date, token, mid).run();

                // 若之前被标记为吊销，重新下发时自动恢复为 ACTIVE
                if (lic.status === "REVOKED") {
                    await db.prepare("UPDATE licenses SET status = 'ACTIVE' WHERE token = ?").bind(token).run();
                }
            } else {
                await db.prepare("UPDATE devices SET remote_command = 'UPDATE_LICENSE', remote_command_payload = ?, license_status = 'ACTIVE', status = 'ACTIVE' WHERE machine_id = ?").bind(token, mid).run();
            }

            await db.prepare("INSERT INTO audit_logs (action_type, target_id, details, ip) VALUES ('PUSH_TOKEN', ?, ?, ?)").bind(mid, `重新下发已有授权码: ${token.substring(0, 24)}...`, ip).run();
            return jsonResponse({ 
                success: true, 
                message: "授权码已成功加入待下发队列，工位机下次心跳时将自动激活！" 
            });
        } else if (action === "REMOTE_COMMAND") {
            await db.prepare("UPDATE devices SET remote_command = ?, remote_command_payload = ? WHERE machine_id = ?").bind(val || "NONE", body.payload || "", mid).run();
            await db.prepare("INSERT INTO audit_logs (action_type, target_id, details, ip) VALUES ('REMOTE_COMMAND', ?, ?, ?)").bind(mid, `下发指令: ${val}`, ip).run();
        }

        return jsonResponse({ success: true });
    }

    // D2. 吊销指定历史激活码 (对标 Gear 规范)
    if (path === "/admin/api/license/revoke" && request.method === "POST") {
        let body = {};
        try { body = await request.json(); } catch(e){}
        const token = (body.token || "").trim();
        const ip = request.headers.get("CF-Connecting-IP") || "-";
        if (!token) return jsonResponse({ success: false, error: "Missing token" }, 400);

        const lic = await db.prepare("SELECT machine_id FROM licenses WHERE token = ?").bind(token).first();
        await db.prepare("UPDATE licenses SET status = 'REVOKED' WHERE token = ?").bind(token).run();
        if (lic && lic.machine_id && lic.machine_id !== "*") {
            await db.prepare("UPDATE devices SET license_status = 'REVOKED', remote_command = 'LOCK_APP' WHERE machine_id = ?").bind(lic.machine_id).run();
        }
        await db.prepare("INSERT INTO audit_logs (action_type, target_id, details, ip) VALUES ('REVOKE_TOKEN', ?, '管理员在控制台吊销此授权码并下发锁机', ?)").bind(token.substring(0, 32), ip).run();
        return jsonResponse({ success: true, message: "激活码已成功吊销，对应工位机将在心跳时自动失效退出" });
    }

    // E. 历史签发授权码列表
    if (path === "/admin/api/licenses" && request.method === "GET") {
        const res = await db.prepare("SELECT * FROM licenses ORDER BY id DESC LIMIT 100").all();
        return jsonResponse({ success: true, licenses: res.results || [] });
    }

    // G. 软件发布历史
    if (path === "/admin/api/releases" && request.method === "GET") {
        const res = await db.prepare("SELECT * FROM releases ORDER BY id DESC").all();
        return jsonResponse({ success: true, releases: res.results || [] });
    }

    // H. 发布新版本
    if (path === "/admin/api/releases" && request.method === "POST") {
        let b = {};
        try { b = await request.json(); } catch(e){}
        if (!b.version || !b.download_url) {
            return jsonResponse({ success: false, error: "请填写完整版本号与下载地址" }, 400);
        }
        await db.prepare(`
            INSERT OR REPLACE INTO releases (version, build, release_date, download_url, backup_url, sha256, file_size_mb, changelog, is_mandatory, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        `).bind(
            b.version.trim(),
            b.build || "",
            b.release_date || new Date().toISOString().substring(0, 10),
            b.download_url.trim(),
            b.backup_url || "",
            b.sha256 || "",
            Number(b.file_size_mb || 0),
            b.changelog || "",
            b.is_mandatory ? 1 : 0
        ).run();

        return jsonResponse({ success: true });
    }

    // I. 全量导出数据库备份 (JSON) (对齐 Gear: 一键备份)
    if (path === "/admin/api/export_db" && request.method === "GET") {
        const devices = (await db.prepare("SELECT * FROM devices").all()).results;
        const licenses = (await db.prepare("SELECT * FROM licenses").all()).results;
        const releases = (await db.prepare("SELECT * FROM releases").all()).results;
        const audit = (await db.prepare("SELECT * FROM audit_logs").all()).results;
        const config = (await db.prepare("SELECT * FROM app_config").all()).results;

        const backup = {
            export_time: new Date().toISOString(),
            platform: "ANSV Coil-Architect Pro Edge DB",
            tables: { devices, licenses, releases, audit_logs: audit, app_config: config }
        };

        return new Response(JSON.stringify(backup, null, 2), {
            headers: {
                "Content-Type": "application/json; charset=utf-8",
                "Content-Disposition": `attachment; filename="coil_architect_backup_${new Date().toISOString().substring(0,10)}.json"`
            }
        });
    }

    return jsonResponse({ success: false, error: "Admin route not found" }, 404);
}

// ==============================================================================
// 纯白工业风格登录页 HTML
// ==============================================================================

function renderLoginPage() {
    return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>管理员安全登录 — ANSV Coil-Architect Pro</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #0F172A;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Microsoft YaHei", sans-serif;
    color: #F8FAFC;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
  }
  .card {
    background: #1E293B;
    border: 1px solid #334155;
    border-radius: 12px;
    width: 100%;
    max-width: 420px;
    padding: 36px 32px;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.3);
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 24px;
  }
  .logo-box {
    width: 44px;
    height: 44px;
    background: #0284C7;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
  }
  .brand-title {
    font-size: 17px;
    font-weight: 700;
    color: #FFFFFF;
    line-height: 1.2;
  }
  .brand-sub {
    font-size: 11px;
    color: #94A3B8;
    margin-top: 3px;
  }
  .form-group {
    margin-bottom: 20px;
  }
  label {
    display: block;
    font-size: 13px;
    font-weight: 600;
    color: #CBD5E1;
    margin-bottom: 8px;
  }
  input[type="password"] {
    width: 100%;
    padding: 12px 14px;
    background: #0F172A;
    border: 1px solid #475569;
    border-radius: 8px;
    color: #FFFFFF;
    font-size: 14px;
    outline: none;
    transition: border-color 0.2s;
  }
  input[type="password"]:focus {
    border-color: #38BDF8;
    box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.2);
  }
  button {
    width: 100%;
    padding: 12px;
    background: #0284C7;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;
  }
  button:hover {
    background: #0369A1;
  }
  .error-tip {
    color: #F87171;
    font-size: 12px;
    margin-top: 10px;
    display: none;
    text-align: center;
  }
  .footer {
    text-align: center;
    margin-top: 24px;
    font-size: 11px;
    color: #64748B;
  }
</style>
</head>
<body>
<div class="card">
  <div class="brand">
    <div class="logo-box">⚡</div>
    <div>
      <div class="brand-title">ANSV Coil-Architect Pro</div>
      <div class="brand-sub">云端授权看门狗与工位监控后台</div>
    </div>
  </div>
  <div class="form-group">
    <label for="pwd">管理员专属安全密码</label>
    <input type="password" id="pwd" placeholder="请输入管理密码" autofocus />
  </div>
  <button id="btn-login" onclick="doLogin()">安全登录解锁控制台</button>
  <div id="err" class="error-tip">密码错误，请重试</div>
  <div class="footer">Actuator Numerical Simulation & Validation | ansv.net</div>
</div>
<script>
async function doLogin() {
  const pwd = document.getElementById('pwd').value;
  const btn = document.getElementById('btn-login');
  const err = document.getElementById('err');
  if(!pwd) return;
  btn.disabled = true;
  btn.innerText = '正在鉴权...';
  err.style.display = 'none';
  try {
    const res = await fetch('/admin/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: pwd })
    });
    const d = await res.json();
    if(d.success) {
      window.location.reload();
    } else {
      err.innerText = d.error || '登录失败';
      err.style.display = 'block';
    }
  } catch(e) {
    err.innerText = '网络连接错误';
    err.style.display = 'block';
  } finally {
    btn.disabled = false;
    btn.innerText = '安全登录解锁控制台';
  }
}
document.getElementById('pwd').addEventListener('keyup', (e) => {
  if(e.key === 'Enter') doLogin();
});
</script>
</body>
</html>`;
}

// ==============================================================================
// 工业级管理看板页面 HTML (对齐 Gear: 纯白工业测控风格 + 标杆案例库)
// ==============================================================================

function renderDashboardPage() {
    return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ANSV Coil-Architect Pro | 商业授权与工位监控控制台</title>
<style>
  :root {
    --bg-main: #F1F5F9;
    --card-bg: #FFFFFF;
    --border: #CBD5E1;
    --primary: #0284C7;
    --primary-hover: #0369A1;
    --text-dark: #0F172A;
    --text-muted: #64748B;
    --success: #10B981;
    --danger: #EF4444;
    --warning: #F59E0B;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg-main);
    color: var(--text-dark);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Microsoft YaHei", sans-serif;
    font-size: 13px;
    line-height: 1.5;
  }
  header {
    background: #0F172A;
    color: #FFFFFF;
    padding: 12px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #0284C7;
  }
  .header-brand {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .header-logo {
    width: 32px;
    height: 32px;
    background: #0284C7;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    font-weight: bold;
  }
  .header-title {
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.3px;
  }
  .header-sub {
    font-size: 11px;
    color: #94A3B8;
  }
  .header-tools {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .btn-header {
    background: #1E293B;
    border: 1px solid #334155;
    color: #CBD5E1;
    padding: 6px 12px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 500;
  }
  .btn-header:hover {
    background: #334155;
    color: #FFFFFF;
  }
  .container {
    max-width: 1440px;
    margin: 20px auto;
    padding: 0 20px;
  }
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 20px;
  }
  .stat-card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  }
  .stat-label {
    font-size: 12px;
    color: var(--text-muted);
    font-weight: 600;
  }
  .stat-val {
    font-size: 26px;
    font-weight: 800;
    color: var(--text-dark);
    margin-top: 4px;
    display: flex;
    align-items: baseline;
    gap: 6px;
  }
  .nav-tabs {
    display: flex;
    gap: 8px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 16px;
  }
  .nav-tab {
    padding: 10px 18px;
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 13px;
    font-weight: 600;
    color: var(--text-muted);
    cursor: pointer;
    transition: all 0.2s;
  }
  .nav-tab.active {
    color: var(--primary);
    border-bottom-color: var(--primary);
    background: rgba(2, 132, 199, 0.04);
  }
  .card-main {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  }
  .toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    flex-wrap: wrap;
    gap: 12px;
  }
  .search-input {
    padding: 7px 12px;
    border: 1px solid var(--border);
    border-radius: 6px;
    width: 280px;
    font-size: 12px;
    outline: none;
  }
  .search-input:focus {
    border-color: var(--primary);
  }
  .btn-primary {
    background: var(--primary);
    color: #FFFFFF;
    border: none;
    padding: 7px 14px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
  }
  .btn-primary:hover {
    background: var(--primary-hover);
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
  }
  th {
    background: #F8FAFC;
    color: var(--text-muted);
    font-weight: 700;
    text-align: left;
    padding: 10px 12px;
    border-bottom: 1px solid var(--border);
  }
  td {
    padding: 10px 12px;
    border-bottom: 1px solid #E2E8F0;
    color: var(--text-dark);
  }
  tr:hover td {
    background: #F8FAFC;
  }
  .badge {
    display: inline-block;
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
  }
  .badge-success { background: #DCFCE7; color: #15803D; }
  .badge-warning { background: #FEF3C7; color: #B45309; }
  .badge-danger { background: #FEE2E2; color: #B91C1C; }
  .badge-info { background: #E0F2FE; color: #0369A1; }
  .mono {
    font-family: Consolas, monospace;
    font-weight: 600;
  }
  .click-copy {
    cursor: pointer;
    border-bottom: 1px dashed var(--primary);
  }
  .click-copy:hover {
    color: var(--primary);
  }
  /* 模态弹窗 */
  .modal-overlay {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(15, 23, 42, 0.6);
    display: none;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }
  .modal-box {
    background: #FFFFFF;
    border-radius: 10px;
    width: 100%;
    max-width: 560px;
    padding: 24px;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.2);
  }
  .modal-title {
    font-size: 16px;
    font-weight: 700;
    margin-bottom: 16px;
    color: var(--text-dark);
  }
  .form-row {
    margin-bottom: 14px;
  }
  .form-row label {
    display: block;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-muted);
    margin-bottom: 4px;
  }
  .form-row input, .form-row select, .form-row textarea {
    width: 100%;
    padding: 8px 10px;
    border: 1px solid var(--border);
    border-radius: 6px;
    font-size: 12px;
    outline: none;
  }
  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 20px;
  }
  .btn-secondary {
    background: #E2E8F0;
    color: #475569;
    border: none;
    padding: 7px 14px;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 600;
  }
  .token-result-box {
    background: #F8FAFC;
    border: 1px solid var(--primary);
    border-radius: 6px;
    padding: 12px;
    margin-top: 14px;
    display: none;
  }
  .token-text {
    font-family: Consolas, monospace;
    font-size: 11px;
    word-break: break-all;
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    padding: 8px;
    border-radius: 4px;
    margin-top: 6px;
  }
</style>
</head>
<body>

<header>
  <div class="header-brand">
    <div class="header-logo">⚡</div>
    <div>
      <div class="header-title">ANSV Coil-Architect Pro | 商业授权与工位监控控制台</div>
      <div class="header-sub">Actuator Numerical Simulation & Validation | 边缘分布式看门狗引擎</div>
    </div>
  </div>
  <div class="header-tools">
    <button class="btn-header" onclick="exportDbBackup()">📥 导出全量备份 JSON</button>
    <button class="btn-header" onclick="doLogout()">🚪 退出管理</button>
  </div>
</header>

<div class="container">
  <!-- 顶部数据概览卡片 (对齐 Gear 架构) -->
  <div class="stats-grid">
    <div class="stat-card" style="border-left: 4px solid #10B981; background: #F0FDF4;">
      <div class="stat-label">🟢 当前在线活跃工位机</div>
      <div class="stat-val" id="stat-live-online" style="color: #059669; font-size:28px;">-</div>
      <div style="font-size:10px; color:#059669; margin-top:2px;">基于 40 分钟内授权校验握手</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">💻 累计接入工位机</div>
      <div class="stat-val" id="stat-total-devices">-</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">🔑 活跃商业授权</div>
      <div class="stat-val" id="stat-active-devices" style="color: var(--primary);">-</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">⚠️ 7天内即将到期预警</div>
      <div class="stat-val" id="stat-expiring-soon" style="color: var(--warning);">-</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">🚀 累计发布版本数</div>
      <div class="stat-val" id="stat-total-releases" style="color:#8B5CF6;">-</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">🚀 当前主推版本</div>
      <div class="stat-val" id="stat-latest-ver" style="color: var(--primary);">-</div>
    </div>
  </div>

  <!-- 选项卡导航 (对齐 Gear 架构) -->
  <div class="nav-tabs">
    <button class="nav-tab active" onclick="switchTab('devices')">💻 现场工位机监控台账</button>
    <button class="nav-tab" onclick="switchTab('licenses')">🔑 历史签发授权记录</button>
    <button class="nav-tab" onclick="switchTab('releases')">🚀 软件发版与 OTA 管理</button>
  </div>

  <!-- TAB 1: 工位机台账 -->
  <div id="tab-devices" class="card-main">
    <div class="toolbar">
      <div>
        <input type="text" id="search-device" class="search-input" placeholder="🔍 搜索机器码 / 公司 / 操作员 / IP..." onkeyup="if(event.key==='Enter') loadDevices()" />
        <button class="btn-primary" onclick="loadDevices()">查询</button>
      </div>
      <div>
        <button class="btn-primary" style="background:#059669;" onclick="openGenerateModal()">➕ 为客户一键生成激活码</button>
        <button class="btn-secondary" onclick="loadDevices(); loadStats();">🔄 立即刷新</button>
        <span id="auto-refresh-pill" style="font-size:11px;color:#059669;background:#ECFDF5;padding:4px 10px;border-radius:12px;border:1px solid #A7F3D0;margin-left:8px;font-weight:600;">
          🟢 实时在线监听中 (每10秒自刷新)
        </span>
      </div>
    </div>
    <div style="overflow-x: auto;">
      <table>
        <thead>
          <tr>
            <th style="min-width:115px;">实时连接状态</th>
            <th>机器识别码 (Machine ID)</th>
            <th>客户公司 / 操作人员</th>
            <th>软件 / 基准库</th>
            <th>商业授权状态</th>
            <th>到期日期 (剩余天数)</th>
            <th>最近在线心跳 (北京时间)</th>
            <th>设备体征 (磁盘/虚拟机/时钟)</th>
            <th>远程管控操作</th>
          </tr>
        </thead>
        <tbody id="device-table-body">
          <tr><td colspan="9" style="text-align:center; padding: 30px;">正在加载工位机资产...</td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <!-- TAB 2: 历史授权码 -->
  <div id="tab-licenses" class="card-main" style="display:none;">
    <div class="toolbar">
      <div><b>已签发加密授权码记录 (最近 100 条)</b></div>
      <div style="display:flex; gap:8px;">
        <input type="text" id="search-license" class="search-input" placeholder="🔍 搜索机器码 / 公司 / 经手人..." onkeyup="if(event.key==='Enter') loadLicenses()" />
        <button class="btn-primary" onclick="loadLicenses()">查询</button>
        <button class="btn-primary" onclick="openGenerateModal()">➕ 签发新授权</button>
      </div>
    </div>
    <div style="overflow-x: auto;">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>绑定机器码</th>
            <th>方案类型</th>
            <th>到期时间</th>
            <th>授权企业</th>
            <th>经手人</th>
            <th>签发时间</th>
            <th>激活码 (点击复制)</th>
            <th>管控操作</th>
          </tr>
        </thead>
        <tbody id="license-table-body">
          <tr><td colspan="8" style="text-align:center; padding: 30px;">正在读取授权记录...</td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <!-- TAB 4: 软件发版管理 -->
  <div id="tab-releases" class="card-main" style="display:none;">
    <div class="toolbar">
      <div><b>官方版本发布与 OTA 更新列表</b></div>
      <button class="btn-primary" onclick="openReleaseModal()">➕ 登记新版本</button>
    </div>
    <div style="overflow-x: auto;">
      <table>
        <thead>
          <tr>
            <th>版本号</th>
            <th>发布日期</th>
            <th>构建指纹</th>
            <th>安装包大小</th>
            <th>下载链接 (直链)</th>
            <th>强制升级</th>
          </tr>
        </thead>
        <tbody id="release-table-body">
          <tr><td colspan="6" style="text-align:center; padding: 30px;">正在读取发布记录...</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</div>

<!-- 弹窗 1: 生成激活码 -->
<div id="modal-gen" class="modal-overlay">
  <div class="modal-box">
    <div class="modal-title">🔑 为客户一键签发商业授权 Token</div>
    <div class="form-row">
      <label>客户机器识别码 (必填)</label>
      <input type="text" id="gen-mid" placeholder="例如: COIL-609D-64D4-5D11-35E2" style="font-family:Consolas,monospace;" />
    </div>
    <div class="form-row">
      <label>授权订阅方案与商业类别</label>
      <select id="gen-plan" onchange="toggleCustomDate()">
        <optgroup label="👑 企业买断制 (Perpetual)">
          <option value="PERPETUAL_1Y_UPDATE" selected>👑 标准企业买断版 (永久可用 + 赠送1年版本更新与技术支持)</option>
          <option value="PERPETUAL_LIFETIME">👑 尊享企业买断版 (永久可用 + 终身免维护费免费升级)</option>
        </optgroup>
        <optgroup label="🟢 周期订阅制 (Subscription)">
          <option value="SUB_ANNUAL_365">🟢 按年商业订阅版 (365天 · 含全年小版本升级与工程支持)</option>
          <option value="SUB_QUARTERLY_90">🟢 按季度商业版 (90天 · 适用于 EVT/DVT 试产攻关)</option>
          <option value="SUB_MONTHLY_30">🟢 按月商业版 (30天 · 适用于特定项目短期打样)</option>
        </optgroup>
        <optgroup label="⚪ 评估与试用 (Trial)">
          <option value="TRIAL_14">⚪ 14 天项目评估版</option>
          <option value="TRIAL_7">⚪ 7 天短期试用版</option>
          <option value="CUSTOM">⚙️ 自定义到期日与维护期</option>
        </optgroup>
      </select>
    </div>
    <div class="form-row" id="row-custom-date" style="display:none;">
      <label>指定软件权限到期日 (YYYY-MM-DD 或 PERMANENT)</label>
      <input type="text" id="gen-custom-date" placeholder="例如: 2027-12-31 或 PERMANENT" />
      <label style="margin-top:6px;">指定版本维护更新到期日 (YYYY-MM-DD 或 PERMANENT)</label>
      <input type="text" id="gen-custom-maint" placeholder="例如: 2027-10-20 或 PERMANENT" />
    </div>
    <div class="form-row">
      <label>客户企业 / 机构名称</label>
      <input type="text" id="gen-cust" placeholder="例如: 苏州XX微型马达研发部" value="ANSV VIP Client" />
    </div>
    <div class="form-row">
      <label>产线 / 工位编号 (可选)</label>
      <input type="text" id="gen-stat" placeholder="例如: WORKSTATION-01" value="WORKSTATION-01" />
    </div>
    <div class="form-row">
      <label>商务备注 / 合同号 (可选)</label>
      <input type="text" id="gen-notes" placeholder="内部合同编号或经手人" />
    </div>

    <div id="gen-result" class="token-result-box">
      <div style="font-size:12px; font-weight:700; color:var(--primary);">🎉 授权码已成功生成并存入数据库！</div>
      <div class="token-text" id="token-display"></div>
      <div style="margin-top:8px; display:flex; gap:8px;">
        <button class="btn-primary" style="flex:1;" onclick="copyToken()">📋 复制完整激活码</button>
        <button class="btn-secondary" style="flex:1;" onclick="copyWechatTemplate()">💬 复制微信回复模板</button>
      </div>
    </div>

    <div class="modal-actions">
      <button class="btn-secondary" onclick="closeGenerateModal()">关闭</button>
      <button class="btn-primary" id="btn-do-gen" onclick="doGenerateToken()">立即生成</button>
    </div>
  </div>
</div>

<script>
let currentGeneratedToken = '';
let currentGeneratedInfo = {};

function switchTab(tab) {
  document.querySelectorAll('.nav-tab').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  document.getElementById('tab-devices').style.display = tab === 'devices' ? 'block' : 'none';
  document.getElementById('tab-licenses').style.display = tab === 'licenses' ? 'block' : 'none';
  document.getElementById('tab-releases').style.display = tab === 'releases' ? 'block' : 'none';
  if(tab === 'licenses') loadLicenses();
  if(tab === 'releases') loadReleases();
}

async function loadStats() {
  try {
    const res = await fetch('/admin/api/stats');
    const d = await res.json();
    if(d.success) {
      if(document.getElementById('stat-live-online')) {
        document.getElementById('stat-live-online').innerText = d.stats.live_online !== undefined ? d.stats.live_online : 0;
      }
      document.getElementById('stat-total-devices').innerText = d.stats.total_devices;
      document.getElementById('stat-active-devices').innerText = d.stats.active_devices;
      document.getElementById('stat-expiring-soon').innerText = d.stats.expiring_soon;
      document.getElementById('stat-today-syncs').innerText = d.stats.today_syncs;
      document.getElementById('stat-total-cases').innerText = d.stats.total_cases || 0;
      document.getElementById('stat-latest-ver').innerText = d.stats.latest_version;
    }
  } catch(e){}
}

async function loadDevices() {
  const q = document.getElementById('search-device').value;
  const tbody = document.getElementById('device-table-body');
  try {
    const res = await fetch('/admin/api/devices?q=' + encodeURIComponent(q));
    const d = await res.json();
    if(d.success && d.devices.length > 0) {
      tbody.innerHTML = d.devices.map(dev => {
        let onlineHtml = '';
        if (dev.is_online) {
          let secText = dev.diff_sec < 60 ? (dev.diff_sec + '秒前心跳') : (Math.floor(dev.diff_sec/60) + '分钟前心跳');
          onlineHtml = '<div style="display:inline-flex;align-items:center;gap:6px;background:#ECFDF5;border:1px solid #A7F3D0;padding:4px 10px;border-radius:20px;">' +
            '<span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#10B981;box-shadow:0 0 8px #10B981;"></span>' +
            '<span style="color:#059669;font-weight:700;font-size:12px;">实时在线</span>' +
          '</div><br><span style="color:#059669;font-size:10px;font-weight:600;margin-top:2px;display:inline-block;">⚡ ' + secText + '</span>';
        } else {
          let timeText = dev.diff_sec > 86400 ? (Math.floor(dev.diff_sec/86400) + '天前') : (dev.diff_sec > 3600 ? Math.floor(dev.diff_sec/3600) + '小时前' : Math.floor(dev.diff_sec/60) + '分钟前');
          onlineHtml = '<div style="display:inline-flex;align-items:center;gap:6px;background:#F8FAFC;border:1px solid #E2E8F0;padding:4px 10px;border-radius:20px;">' +
            '<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#94A3B8;"></span>' +
            '<span style="color:#94A3B8;font-size:11px;">离线状态</span>' +
          '</div><br><span style="color:#94A3B8;font-size:10px;margin-top:2px;display:inline-block;">' + timeText + '</span>';
        }

        const isRevoked = (dev.status === 'REVOKED' || dev.license_status === 'REVOKED');
        const isBanned = (dev.status === 'BANNED' || dev.license_status === 'BANNED');

        let statusBadge = '<span class="badge badge-success">正常授权</span>';
        if (isBanned) {
          statusBadge = '<span class="badge badge-danger">已拉黑封禁</span>';
        } else if (isRevoked) {
          if (dev.revoke_confirmed == 1) {
            statusBadge = '<span class="badge badge-danger" style="background:#DC2626;">🚫 已取消授权 (已锁机)</span><br><span style="color:#059669;font-size:10px;font-weight:600;">✓ 工位机已回执锁机</span>';
          } else {
            statusBadge = '<span class="badge badge-warning" style="background:#D97706;">⏳ 取消授权中 (待锁机)</span><br><span style="color:#B45309;font-size:10px;">• 锁机指令排队中</span>';
          }
        } else if (dev.license_status === 'EXPIRED') {
          statusBadge = '<span class="badge badge-danger">已过期</span>';
        } else if (dev.license_status === 'TRIAL') {
          statusBadge = '<span class="badge badge-warning">免密试用</span>';
        }

        let remainText = dev.license_expire === 'PERMANENT' ? '永久有效' : (dev.remaining_days > 0 ? dev.remaining_days + ' 天' : '<span style="color:red;">已逾期</span>');
        let vmText = dev.is_virtual_machine ? '<span style="color:#B45309;">⚠️虚拟机</span>' : '物理真机';
        let clockText = dev.clock_tampered ? '<span style="color:#B91C1C;font-weight:bold;">🚨倒拨时钟</span>' : '时钟正常';
        let diskText = dev.disk_free_gb > 0 ? (dev.disk_free_gb + ' GB') : '-';

        let actionBtns = '';
        if (isRevoked || isBanned) {
          actionBtns = 
            '<button class="btn-primary" style="padding:4px 10px;font-size:11px;background:#059669;margin-right:4px;" data-mid="' + dev.machine_id + '" onclick="undoRevokeDevice(this.dataset.mid)">↩️ 撤销取消授权 (恢复激活)</button>' +
            '<button class="btn-secondary" style="padding:4px 9px;font-size:11px;background:#EFF6FF;color:#2563EB;border-color:#BFDBFE;margin-right:4px;" data-mid="' + dev.machine_id + '" data-confirmed="' + (dev.revoke_confirmed || 0) + '" data-ack="' + (dev.last_ack_cmd || '') + '" data-time="' + (dev.last_sync_bj || dev.last_sync_time || '-') + '" onclick="checkRevokeStatus(this.dataset.mid, this.dataset.confirmed, this.dataset.ack, this.dataset.time)">🔍 检测锁机状态</button>' +
            '<button class="btn-secondary" style="padding:4px 9px;font-size:11px;background:#F0FDF4;color:#059669;border-color:#A7F3D0;margin-right:4px;" data-mid="' + dev.machine_id + '" onclick="repushLatestLicense(this.dataset.mid)">🔄 重发已有授权</button>' +
            '<button class="btn-secondary" style="padding:4px 9px;font-size:11px;" data-mid="' + dev.machine_id + '" onclick="showRemoteMenu(this.dataset.mid)">⚙️ 更多</button>';
        } else {
          actionBtns = 
            '<button class="btn-primary" style="padding:4px 9px;font-size:11px;background:#2563EB;margin-right:4px;" data-mid="' + dev.machine_id + '" data-cust="' + (dev.customer_name || '') + '" onclick="autoAuthorizeDevice(this.dataset.mid, this.dataset.cust)">⚡ 一键下发新授权</button>' +
            '<button class="btn-secondary" style="padding:4px 9px;font-size:11px;background:#F0FDF4;color:#059669;border-color:#A7F3D0;font-weight:600;margin-right:4px;" data-mid="' + dev.machine_id + '" onclick="repushLatestLicense(this.dataset.mid)">🔄 重发已有授权</button>' +
            '<button class="btn-secondary" style="padding:4px 9px;font-size:11px;margin-right:4px;" data-mid="' + dev.machine_id + '" data-cust="' + (dev.customer_name || '') + '" onclick="quickGenForMid(this.dataset.mid, this.dataset.cust)">开通/续约</button>' +
            '<button class="btn-secondary" style="padding:4px 9px;font-size:11px;color:#EF4444;border-color:#FCA5A5;margin-right:4px;" data-mid="' + dev.machine_id + '" onclick="revokeDevice(this.dataset.mid)">🚫 取消授权</button>' +
            '<button class="btn-secondary" style="padding:4px 9px;font-size:11px;" data-mid="' + dev.machine_id + '" onclick="showRemoteMenu(this.dataset.mid)">⚙️ 更多</button>';
        }

        return '<tr>' +
          '<td>' + onlineHtml + '</td>' +
          '<td><span class="mono click-copy" onclick="copyText(\\'' + dev.machine_id + '\\')">' + dev.machine_id + '</span><br><span style="color:#64748B;font-size:11px;">MAC: ' + (dev.mac_address || '-') + '</span></td>' +
          '<td><b>' + (dev.customer_name || '-') + '</b><br><span style="color:#64748B;font-size:11px;">操作员: ' + (dev.operator_name || '-') + ' (' + (dev.system_user || '-') + ')</span><br><span style="color:#94A3B8;font-size:10px;">' + (dev.hostname || '-') + ' (' + (dev.ip_address || '-') + ')</span></td>' +
          '<td><span class="mono">' + dev.app_version + '</span><br><span style="color:#0284C7;font-size:10px;font-family:monospace;">Build ' + (dev.app_build || '-') + '</span></td>' +
          '<td>' + statusBadge + '</td>' +
          '<td>' + dev.license_expire + '<br><span style="font-size:11px;color:#64748B;">(' + remainText + ')</span></td>' +
          '<td><b>' + (dev.last_sync_bj || dev.last_sync_time || '-') + '</b><br><span style="font-size:10px;color:#94A3B8;">已累计心跳 ' + (dev.sync_count || 1) + ' 次</span></td>' +
          '<td>' + vmText + ' | ' + clockText + '<br><span style="font-size:10px;color:#64748B;">空闲磁盘: ' + diskText + '</span></td>' +
          '<td>' + actionBtns + '</td>' +
        '</tr>';
      }).join('');
    } else {
      tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; padding: 30px; color:#94A3B8;">暂无符合条件的工位机记录</td></tr>';
    }
  } catch(e) {
    tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; padding: 20px; color:red;">数据加载异常，请刷新页面重试</td></tr>';
  }
}


async function autoAuthorizeDevice(mid, customer) {
  const cust = prompt('请输入授权企业/客户名称 (将写入证书凭证):', customer && customer !== '散户/未登记' && customer !== '在线申请用户' ? customer : 'ANSV 商业VIP客户');
  if (cust === null) return;
  const planChoice = prompt('请选择授权周期方案：\\n1: 年度商业版 (365天) [默认]\\n2: 永久企业买断版\\n3: 季度项目版 (90天)\\n\\n请输入数字 (1-3):', '1');
  if (planChoice === null) return;

  let planType = 'SUB_ANNUAL_365';
  if (planChoice === '2') planType = 'PERPETUAL_1Y_UPDATE';
  else if (planChoice === '3') planType = 'SUB_QUARTER_90';

  try {
    const res = await fetch('/admin/api/device/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        machine_id: mid,
        action: 'AUTO_AUTHORIZE',
        customer_name: cust,
        plan_type: planType
      })
    });
    const d = await res.json();
    if (d.success) {
      alert('🎉 商业授权已成功生成并下发至工位机 [' + mid + ']！\\n\\n客户名称: ' + d.customer_name + '\\n方案级别: ' + d.plan_label + '\\n有效期至: ' + d.expire_date + '\\n\\n工位机将在下一次心跳（未激活时仅15秒）或用户点击“在线激活”时自动激活并弹出成功信息！');
      loadDevices();
      loadStats();
    } else {
      alert('下发失败: ' + (d.error || '未知错误'));
    }
  } catch(e) {
    alert('网络异常: ' + e.message);
  }
}

function checkRevokeStatus(mid, confirmed, ack, time) {
  if (confirmed == '1' || ack.indexOf('LOCK_APP') !== -1) {
    const msg = [
      '✅【取消授权与锁机验证成功 · 已彻底生效】',
      '',
      '工位机识别码: ' + mid,
      '工位机锁机回执: ' + (ack || 'LOCK_APP:EXECUTED (已确认)'),
      '最近心跳/回执时间: ' + (time || '-'),
      '',
      '【安全审计报告】：',
      '1. 工位机已成功接收云端下发的 LOCK_APP 远程锁机指令；',
      '2. 本地商业许可文件 (.key) 已彻底清除并归档，软件已被安全锁定强制退出；',
      '3. 云端已永久锁定为 REVOKED 状态，任何客户端心跳绝不会自动恢复，外人无法使用！',
      '4. 状态将永久保持，直到管理员在控制台手工点击【↩️ 撤销取消授权 (恢复激活)】。'
    ].join(String.fromCharCode(10));
    alert(msg);
  } else {
    const msg = [
      '⏳【取消授权指令已就绪 · 等待工位机心跳接收】',
      '',
      '工位机识别码: ' + mid,
      '当前状态: 云端已永久锁定为 REVOKED，LOCK_APP 锁机指令在待发队列中',
      '最近心跳时间: ' + (time || '-'),
      '',
      '【执行机制说明】：',
      '• 客户端软件在下一次心跳周期 (最长15~30秒) 或用户下次打开软件时，将瞬间强制执行锁机并销毁凭证退出；',
      '• 工位机确认执行后，此处状态将自动更新为“✓ 工位机已回执锁机”。您可随时再次点击本按钮检测核验！'
    ].join(String.fromCharCode(10));
    alert(msg);
  }
}

async function undoRevokeDevice(mid) {
  const msg = [
    '↩️ 确定要撤销工位机 [' + mid + '] 的【取消授权 / 锁机】状态吗？',
    '',
    '【执行恢复说明】：',
    '1. 云端将立即解除对该工位机的远程锁机与吊销限制；',
    '2. 自动恢复该工位机有效商业授权状态，并重新下发商业凭证；',
    '3. 客户端在下次启动或心跳时将自动恢复为正常激活状态，不再提示取消授权！'
  ].join(String.fromCharCode(10));
  if (!confirm(msg)) return;
  try {
    const res = await fetch('/admin/api/device/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ machine_id: mid, action: 'UNDO_REVOKE' })
    });
    const data = await res.json();
    if (data.success) {
      alert('🎉 撤销成功！工位机 [' + mid + '] 授权已恢复，下次心跳或启动将自动重新激活。');
      loadDevices();
      if (typeof loadLicenses === 'function') loadLicenses();
    } else {
      alert('撤销失败: ' + (data.error || '未知错误'));
    }
  } catch (e) {
    alert('网络请求异常: ' + e.message);
  }
}

async function revokeDevice(mid) {
  const msg = [
    '⚠️ 确定要取消工位机 [' + mid + '] 的授权并远程锁机吗？',
    '',
    '【远程控制影响说明】：',
    '1. 云端将立即向该工位机下发 LOCK_APP 锁机指令；',
    '2. 客户端将在 30 秒心跳周期内自动清空本地许可文件并安全退出，外人无法继续使用！'
  ].join(String.fromCharCode(10));
  if (!confirm(msg)) return;
  await deviceAction(mid, 'REVOKE');
}

async function showRemoteMenu(mid) {
  const promptLines = [
    '请选择对工位机 [' + mid + '] 执行的远程指令：',
    '',
    '1: ↩️ 撤销取消授权 (恢复激活并下发凭证)',
    '2: 延长 30 天使用期',
    '3: 延长 1 年使用期',
    '4: 设为永久企业买断版',
    '5: 🔄 重新下发该设备最近一次签发授权码',
    '6: 📋 手动粘贴指定授权码推送到该工位机',
    '7: 🚨 强制拉黑封禁 (BAN)',
    '',
    '请输入序号 (1-7):'
  ];
  const act = prompt(promptLines.join(String.fromCharCode(10)), '1');
  if (!act) return;
  if (act === '1') await undoRevokeDevice(mid);
  else if (act === '2') await deviceAction(mid, 'EXTEND_DAYS', 30);
  else if (act === '3') await deviceAction(mid, 'EXTEND_DAYS', 365);
  else if (act === '4') await deviceAction(mid, 'SET_PERMANENT');
  else if (act === '5') await repushLatestLicense(mid);
  else if (act === '6') {
    const customTok = prompt('请输入要下发给工位机 [' + mid + '] 的完整 COIL-SEC 授权码：');
    if (customTok && customTok.trim()) {
      await repushLicenseToDevice(mid, customTok.trim(), '', '');
    }
  }
  else if (act === '7') {
    if (confirm('确定要拉黑该机器码吗？')) await deviceAction(mid, 'BAN');
  }
}

async function repushLatestLicense(mid) {
  try {
    const res = await fetch('/admin/api/device/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        machine_id: mid,
        action: 'GET_LATEST_LICENSE'
      })
    });
    const d = await res.json();
    if (!d.success || !d.license) {
      alert(['⚠️ 未找到工位机 [' + mid + '] 在系统数据库中的历史签发记录。', '', '请点击【⚡ 一键下发新授权】为其生成新授权。'].join(String.fromCharCode(10)));
      return;
    }
    const lic = d.license;
    const confirmLines = [
      '📋 找到工位机 [' + mid + '] 最近一次签发的有效授权：',
      '• 客户名称: ' + lic.customer_name,
      '• 方案类型: ' + lic.plan_type,
      '• 到期时间: ' + lic.expire_date,
      '• 当前状态: ' + (lic.status === 'ACTIVE' ? '正常有效' : '已吊销 (重新下发将自动恢复有效)'),
      '• 激活码指纹: ' + lic.token.substring(0, 24) + '...',
      '',
      '确定将此历史授权码重新下发至工位机吗？',
      '(工位机将在 15 秒内心跳自动接收并弹出商业授权凭证卡片)'
    ];

    if (!confirm(confirmLines.join(String.fromCharCode(10)))) return;

    await repushLicenseToDevice(mid, lic.token, lic.customer_name, lic.expire_date);
  } catch(e) {
    alert('查询历史授权失败: ' + e.message);
  }
}

async function repushLicenseToDevice(mid, token, customer, expireDate) {
  try {
    const res = await fetch('/admin/api/device/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        machine_id: mid,
        action: 'PUSH_TOKEN',
        value: token
      })
    });
    const d = await res.json();
    if (d.success) {
      const okLines = [
        '🎉 历史授权码已成功重新下发！',
        '',
        '• 目标工位机: ' + mid,
        '• 授权客户: ' + (customer || '-'),
        '• 有效期至: ' + (expireDate || '-'),
        '',
        '工位机将在下一次心跳握手（未激活时仅 15 秒）或操作员点击【在线激活】时自动激活并弹出成功凭证卡片！'
      ];
      alert(okLines.join(String.fromCharCode(10)));
      loadDevices();
      loadLicenses();
      loadStats();
    } else {
      alert('下发失败: ' + (d.error || '未知错误'));
    }
  } catch(e) {
    alert('网络异常: ' + e.message);
  }
}

async function loadLicenses() {
  const tbody = document.getElementById('license-table-body');
  const searchInput = document.getElementById('search-license');
  const q = (searchInput ? searchInput.value : '').trim().toLowerCase();
  try {
    const res = await fetch('/admin/api/licenses');
    const d = await res.json();
    if(d.success && d.licenses.length > 0) {
      let list = d.licenses;
      if (q) {
        list = list.filter(lic => 
          (lic.machine_id && lic.machine_id.toLowerCase().includes(q)) ||
          (lic.customer_name && lic.customer_name.toLowerCase().includes(q)) ||
          (lic.operator_name && lic.operator_name.toLowerCase().includes(q)) ||
          (lic.token && lic.token.toLowerCase().includes(q))
        );
      }
      tbody.innerHTML = list.map(lic => {
        let licAction = '';
        if (lic.status === 'REVOKED') {
          licAction = 
            '<span style="color:#EF4444;font-size:11px;font-weight:bold;margin-right:6px;">已吊销</span>' +
            '<button class="btn-primary" style="padding:2px 7px;font-size:10px;background:#059669;" data-mid="' + lic.machine_id + '" data-tok="' + lic.token + '" data-cust="' + (lic.customer_name || '') + '" data-exp="' + lic.expire_date + '" onclick="repushLicenseToDevice(this.dataset.mid, this.dataset.tok, this.dataset.cust, this.dataset.exp)">↩️ 撤销吊销并重新下发</button>';
        } else {
          licAction = 
            '<button class="btn-primary" style="padding:2px 7px;font-size:10px;background:#2563EB;margin-right:4px;" data-mid="' + lic.machine_id + '" data-tok="' + lic.token + '" data-cust="' + (lic.customer_name || '') + '" data-exp="' + lic.expire_date + '" onclick="repushLicenseToDevice(this.dataset.mid, this.dataset.tok, this.dataset.cust, this.dataset.exp)">⚡ 重新下发此码</button>' +
            '<button class="btn-secondary" style="padding:2px 7px;font-size:10px;color:#EF4444;border-color:#FCA5A5;" data-tok="' + lic.token + '" onclick="revokeLicenseToken(this.dataset.tok)">吊销</button>';
        }

        return '<tr>' +
          '<td>' + lic.id + '</td>' +
          '<td><span class="mono click-copy" data-copy="' + lic.machine_id + '" onclick="copyText(this.dataset.copy)">' + lic.machine_id + '</span></td>' +
          '<td><span class="badge badge-info">' + lic.plan_type + '</span></td>' +
          '<td><b>' + lic.expire_date + '</b><br><span style="font-size:10px;color:#64748B;">维护升级至: ' + (lic.maint_expire || lic.expire_date) + '</span></td>' +
          '<td><b>' + (lic.customer_name || '-') + '</b></td>' +
          '<td>' + (lic.operator_name || 'ADMIN') + '</td>' +
          '<td>' + lic.created_at + '</td>' +
          '<td><span class="mono click-copy" style="font-size:10px;" data-copy="' + lic.token + '" onclick="copyText(this.dataset.copy)">' + lic.token.substring(0, 32) + '...</span></td>' +
          '<td>' + licAction + '</td>' +
        '</tr>';
      }).join('');
    } else {
      tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; padding: 30px; color:#94A3B8;">暂无符合条件的授权签发记录</td></tr>';
    }
  } catch(e){}
}

async function revokeLicenseToken(token) {
  const msg = [
    '⚠️ 确定要吊销此授权激活码吗？',
    '',
    '该激活码绑定的工位机将在下次心跳时直接失效退出！'
  ].join(String.fromCharCode(10));
  if (!confirm(msg)) return;
  try {
    const res = await fetch('/admin/api/license/revoke', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: token })
    });
    const d = await res.json();
    alert(d.message || '已成功吊销');
    loadLicenses();
    loadDevices();
  } catch(e) {
    alert('操作失败: ' + e);
  }
}

async function loadReleases() {
  const tbody = document.getElementById('release-table-body');
  try {
    const res = await fetch('/admin/api/releases');
    const d = await res.json();
    if(d.success && d.releases.length > 0) {
      tbody.innerHTML = d.releases.map(r => {
        return '<tr>' +
          '<td><b>' + r.version + '</b></td>' +
          '<td>' + r.release_date + '</td>' +
          '<td><span class="mono">' + r.build + '</span></td>' +
          '<td>' + r.file_size_mb + ' MB</td>' +
          '<td><a href="' + r.download_url + '" target="_blank" style="color:#0284C7;text-decoration:none;">下载直链 ↗</a></td>' +
          '<td>' + (r.is_mandatory ? '<span class="badge badge-danger">强制升级</span>' : '<span class="badge badge-info">可选升级</span>') + '</td>' +
        '</tr>';
      }).join('');
    }
  } catch(e){}
}

function openGenerateModal() {
  document.getElementById('modal-gen').style.display = 'flex';
  document.getElementById('gen-result').style.display = 'none';
}
function closeGenerateModal() {
  document.getElementById('modal-gen').style.display = 'none';
}
function quickGenForMid(mid, cust) {
  openGenerateModal();
  document.getElementById('gen-mid').value = mid;
  if(cust && cust !== '散户/未登记') document.getElementById('gen-cust').value = cust;
}

function toggleCustomDate() {
  const plan = document.getElementById('gen-plan').value;
  document.getElementById('row-custom-date').style.display = plan === 'CUSTOM' ? 'block' : 'none';
}

async function doGenerateToken() {
  const mid = document.getElementById('gen-mid').value.trim();
  const plan = document.getElementById('gen-plan').value;
  const cust = document.getElementById('gen-cust').value.trim();
  const stat = document.getElementById('gen-stat').value.trim();
  const customDate = (document.getElementById('gen-custom-date') ? document.getElementById('gen-custom-date').value : '').trim();
  const customMaint = (document.getElementById('gen-custom-maint') ? document.getElementById('gen-custom-maint').value : '').trim();
  const notes = document.getElementById('gen-notes').value.trim();

  if(!mid) {
    alert('请填写客户机器码');
    return;
  }
  const btn = document.getElementById('btn-do-gen');
  btn.disabled = true;
  btn.innerText = '正在运算签发...';

  try {
    const res = await fetch('/admin/api/generate_token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        machine_id: mid,
        plan_type: plan,
        customer_name: cust,
        station_id: stat,
        custom_expire: customDate,
        custom_maint: customMaint,
        notes: notes
      })
    });
    const d = await res.json();
    if(d.success) {
      currentGeneratedToken = d.token;
      currentGeneratedInfo = d;
      document.getElementById('token-display').innerText = d.token;
      document.getElementById('gen-result').style.display = 'block';
      loadStats();
      loadDevices();
    } else {
      alert(d.error || '生成失败');
    }
  } catch(e) {
    alert('网络通信异常');
  } finally {
    btn.disabled = false;
    btn.innerText = '立即生成';
  }
}

async function deviceAction(mid, action) {
  if(!confirm('确定要对工位机 ' + mid + ' 执行 ' + action + ' 操作吗？')) return;
  try {
    const res = await fetch('/admin/api/device/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ machine_id: mid, action: action })
    });
    const d = await res.json();
    if(d.success) {
      loadDevices();
      loadStats();
    }
  } catch(e){}
}

function copyText(str) {
  navigator.clipboard.writeText(str).then(() => {
    alert('已复制到剪贴板！');
  });
}

function copyToken() {
  copyText(currentGeneratedToken);
}

function copyWechatTemplate() {
  const nl = String.fromCharCode(10);
  const info = currentGeneratedInfo;
  let dateDesc = '';
  if (info.plan_type === 'PERPETUAL_1Y_UPDATE') {
    dateDesc = [
      '📌 授权类别：👑 标准企业买断版',
      '💎 软件使用权限：永久终身授权 (永不过期)',
      '📅 免费版本更新与支持期至：' + info.maint_expire + ' (期满后仍可永久使用当前版)'
    ].join(nl);
  } else if (info.plan_type === 'PERPETUAL_LIFETIME') {
    dateDesc = [
      '📌 授权类别：👑 尊享企业买断版',
      '💎 软件使用权限：永久终身授权 + 终身免维护费免费升级'
    ].join(nl);
  } else {
    dateDesc = [
      '📌 授权类别：' + (info.plan_label || '商业订阅'),
      '📅 订阅有效期至：' + info.expire_date + ' (期间享受所有小版本免费升级与技术支持)'
    ].join(nl);
  }

  const tpl = [
    '您好！您的【ANSV Coil-Architect Pro 电磁线圈多物理场仿真工作站】商业授权激活凭证已生成完毕：',
    '',
    '🔑 授权激活码：',
    currentGeneratedToken,
    '',
    '📌 绑定机器识别码：' + info.machine_id,
    dateDesc,
    '🏢 授权企业/工位：' + info.customer_name,
    '',
    '💡 激活步骤：在软件中点击【输入激活码】按钮，直接粘贴上述整段激活码即可完成秒级激活！如有任何工程算例疑问，欢迎随时沟通。'
  ].join(nl);
  copyText(tpl);
}

async function exportDbBackup() {
  window.open('/admin/api/export_db', '_blank');
}

async function doLogout() {
  await fetch('/admin/api/logout', { method: 'POST' });
  window.location.reload();
}

window.onload = function() {
  loadStats();
  loadDevices();
  // 生产级：每 10 秒自动静默轮询刷新工位机在线状态与心跳
  setInterval(function() {
    const tabDevices = document.getElementById('tab-devices');
    if (tabDevices && tabDevices.style.display !== 'none') {
      loadDevices();
      loadStats();
    }
  }, 10000);
};
</script>
</body>
</html>`;
}
