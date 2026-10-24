-- ==============================================================================
-- ANSV Coil-Architect Pro | Cloudflare D1 边缘数据库建表与初始化脚本 (v1.2 增强版)
-- 对齐 Gear-NVH / FFT 分析软件 全量工业商业桌面软件云端架构规范
-- 兼容 Cloudflare D1 (Serverless Distributed SQLite)
-- ==============================================================================

-- 1. 设备接入与唯一硬件机器码资产表 (工位机在线监测、操作员追踪、授权到期倒计时、时钟防作弊与远程指令)
CREATE TABLE IF NOT EXISTS devices (
    machine_id VARCHAR(64) PRIMARY KEY,              -- 硬件特征机器码 (如 COIL-609D-64D4-5D11-35E2)
    hostname VARCHAR(128) DEFAULT '-',               -- 电脑主机名
    ip_address VARCHAR(64) DEFAULT '-',              -- 接入外网/内网 IP
    mac_address VARCHAR(64) DEFAULT '-',             -- 物理网卡 MAC 地址
    app_version VARCHAR(32) DEFAULT '-',             -- 客户端运行版本 (如 v1.1.0)
    app_build VARCHAR(32) DEFAULT '-',               -- 客户端编译构建指纹
    wire_db_version VARCHAR(32) DEFAULT 'v1.0',      -- 线模与铜线绝缘层材料基准库版本
    plan_type VARCHAR(32) DEFAULT 'TRIAL',           -- 当前授权模式 (MONTHLY / QUARTERLY / ANNUAL / PERPETUAL_1Y / PERPETUAL_LIFE)
    license_status VARCHAR(32) DEFAULT 'TRIAL',      -- 授权状态 (TRIAL / ACTIVE / EXPIRED / BANNED)
    license_expire VARCHAR(64) DEFAULT '-',          -- 软件运行权限到期日 (YYYY-MM-DD 或 PERMANENT)
    maint_expire VARCHAR(64) DEFAULT '-',            -- 版本更新与维护服务到期日 (YYYY-MM-DD 或 PERMANENT)
    remaining_days INTEGER DEFAULT 0,                -- 剩余有效天数 (负数代表逾期)
    customer_name VARCHAR(128) DEFAULT '散户/未登记', -- 客户企业名称
    line_station VARCHAR(128) DEFAULT 'WORKSTATION-01', -- 所在产线/工位编号
    operator_name VARCHAR(64) DEFAULT '-',           -- 现场操作人员姓名
    operator_id VARCHAR(64) DEFAULT '-',             -- 现场操作人员工号
    system_user VARCHAR(64) DEFAULT '-',             -- Windows 登录操作系统用户名
    is_virtual_machine INTEGER DEFAULT 0,            -- 是否检测到虚拟机环境 (1:是, 0:否)
    disk_free_gb REAL DEFAULT 0.0,                   -- 运行工位机可用磁盘空间 (GB)
    clock_tampered INTEGER DEFAULT 0,                -- 是否检测到本地倒拨时钟作弊 (1:是, 0:否)
    client_clock_time VARCHAR(32) DEFAULT '-',       -- 客户端本地当前时间戳
    clock_skew_sec INTEGER DEFAULT 0,                -- 客户端与云端原子钟偏差秒数
    remote_command VARCHAR(64) DEFAULT 'NONE',       -- 云端下发远程指令 (NONE / LOCK_APP / REFRESH_LICENSE)
    remote_command_payload TEXT DEFAULT '',          -- 远程指令附带参数
    first_seen_time DATETIME DEFAULT CURRENT_TIMESTAMP, -- 首次上线时间
    last_sync_time DATETIME DEFAULT CURRENT_TIMESTAMP,  -- 最近心跳同步时间
    sync_count INTEGER DEFAULT 1,                    -- 累计心跳同步次数
    status VARCHAR(20) DEFAULT 'ACTIVE',             -- 运营管控状态 (ACTIVE / BANNED / FROZEN)
    notes TEXT DEFAULT ''                            -- 管理员商务/工位备注
);

-- 2. 商业授权激活码签发表 (记录由管理员生成的授权 Token 与激活记录)
CREATE TABLE IF NOT EXISTS licenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT NOT NULL UNIQUE,                      -- 生成的 COIL-SEC-... 激活码
    machine_id VARCHAR(64) NOT NULL,                 -- 绑定的目标机器码 (*代表通用通配符)
    plan_type VARCHAR(32) DEFAULT 'SUB_ANNUAL_365',  -- 方案类型 (SUB_MONTHLY_30 / SUB_QUARTERLY_90 / SUB_ANNUAL_365 / PERPETUAL_1Y_UPDATE / PERPETUAL_LIFETIME)
    expire_date VARCHAR(64) NOT NULL,                -- 软件运行权限到期时间 (YYYY-MM-DD 或 PERMANENT)
    maint_expire VARCHAR(64) DEFAULT 'PERMANENT',    -- 版本更新与维护服务到期日 (YYYY-MM-DD 或 PERMANENT)
    customer_name VARCHAR(128) DEFAULT 'ANSV VIP Client', -- 授权客户/公司
    station_id VARCHAR(64) DEFAULT 'WORKSTATION-01', -- 工位代号
    operator_name VARCHAR(64) DEFAULT 'ADMIN',       -- 经手签发人
    status VARCHAR(32) DEFAULT 'ACTIVE',             -- 状态 (ACTIVE:有效, REVOKED:已吊销, EXPIRED:已过期)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,   -- 签发时间
    activated_at DATETIME,                           -- 客户端首次激活时间
    notes TEXT DEFAULT ''                            -- 商务合作合同/经手人备注
);

-- 4. 管理员操作与安全审计留痕表 (不可篡改留痕，IATF 16949 / ISO 9001 质量溯源)
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type VARCHAR(64) NOT NULL,                -- 操作类型 (GENERATE_TOKEN, BAN_DEVICE, EXTEND_LICENSE, OTA_PUBLISH)
    target_id VARCHAR(64) DEFAULT '',                -- 目标机器码或目标对象
    operator_name VARCHAR(64) DEFAULT 'ADMIN',       -- 操作人
    reason TEXT DEFAULT '',                          -- 操作原因
    details TEXT DEFAULT '',                         -- 操作详情明细 (JSON 或参数文本)
    ip VARCHAR(64) DEFAULT '',                       -- 操作人公网 IP
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 5. 软件本体版本发布与 OTA 更新履历表
CREATE TABLE IF NOT EXISTS releases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version VARCHAR(32) NOT NULL UNIQUE,             -- 版本号 (如 v1.1.0)
    build VARCHAR(64) DEFAULT '',                    -- 构建编号 (如 20261014_B1)
    release_date VARCHAR(32) NOT NULL,               -- 发布日期 (YYYY-MM-DD)
    download_url TEXT NOT NULL,                      -- 主下载直链 (GitHub Releases / CDN)
    backup_url TEXT DEFAULT '',                      -- 备用高速镜像下载直链
    sha256 VARCHAR(64) DEFAULT '',                   -- 官方发布包 SHA-256 校验和
    file_size_mb REAL DEFAULT 0.0,                   -- 安装包体积 (MB)
    changelog TEXT DEFAULT '',                       -- 本次版本更新详细说明 (Markdown)
    is_mandatory INTEGER DEFAULT 0,                  -- 是否强制升级 (0:建议, 1:强制阻断旧版)
    is_active INTEGER DEFAULT 1,                     -- 是否作为当前主推版本
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 6. 系统全局键值配置表 (保存全局通告、主推版本与运营参数)
CREATE TABLE IF NOT EXISTS app_config (
    meta_key TEXT PRIMARY KEY,
    meta_value TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 7. 索引优化 (保障百万级查询毫秒响应)
CREATE INDEX IF NOT EXISTS idx_devices_last_sync ON devices(last_sync_time);
CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
CREATE INDEX IF NOT EXISTS idx_licenses_mid ON licenses(machine_id);
CREATE INDEX IF NOT EXISTS idx_licenses_token ON licenses(token);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);

-- ==============================================================================
-- 初始基准数据注入
-- ==============================================================================

-- 写入当前官方正式发布版本 (2027 年度正式版)
INSERT OR REPLACE INTO releases (version, build, release_date, download_url, backup_url, sha256, file_size_mb, changelog, is_mandatory, is_active)
VALUES (
    '2027',
    '20261024B6',
    '2026-10-24',
    'https://github.com/tonychen5577-tech/coil-architect/releases/download/2027/ANSV_Coil_Architect_Pro_2027_Full.zip',
    'https://github.com/tonychen5577-tech/coil-architect/releases/download/2027/ANSV_Coil_Architect_Pro_2027_Incremental_Patch.zip',
    'a2d8f0920b981f4764d4c8cf2182940cf04075729c9c1f48db0cf6035fbc3f4f',
    81.92,
    '### ANSV Coil-Architect Pro 2027 官方年度正式版 (Build 20261024B6)
- 🌟 核心算法与拓扑：优化微观多层密排绕线算法与实际截面拓扑（支持不在同一层出现的绕线计算）；
- 📊 报表与方案比对：强化 Excel 仿真报告自适应导出，方案比对抽屉补齐内长内宽等几何指标并支持方案导入导出与现场还原；
- 🛡️ 工业授权与网络：支持一键云端在线极速授权与15秒自适应心跳；
- 📖 双语手册全量内置：中英双语离线说明书与非同层截面图全量打包，F1 一键本地离线查看。',
    0,
    1
);


-- 写入全局配置项
INSERT OR REPLACE INTO app_config (meta_key, meta_value) VALUES 
('latest_version', 'v1.1.0'),
('official_site', 'https://ansv.net'),
('github_repo', 'https://github.com/tonychen5577-tech/coil-architect'),
('support_email', 'support@ansv.net'),
('announcement', '欢迎使用 ANSV Coil-Architect Pro 工业电磁线圈多物理场仿真工作站！');
