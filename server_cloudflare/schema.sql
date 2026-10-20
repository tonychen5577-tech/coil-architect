-- ==============================================================================
-- ANSV Coil-Architect Pro | Cloudflare D1 边缘数据库建表与初始化脚本
-- 兼容 Cloudflare D1 (Serverless Distributed SQLite)
-- ==============================================================================

-- 1. 设备接入与唯一硬件机器码资产台账表 (工位机在线监测、授权到期倒计时与防倒拨时钟)
CREATE TABLE IF NOT EXISTS devices (
    machine_id VARCHAR(64) PRIMARY KEY,              -- 硬件特征机器码 (如 COIL-609D-64D4-5D11-35E2)
    hostname VARCHAR(128) DEFAULT '-',               -- 电脑主机名
    ip_address VARCHAR(64) DEFAULT '-',              -- 接入外网/内网 IP
    mac_address VARCHAR(64) DEFAULT '-',             -- 物理网卡 MAC 地址
    app_version VARCHAR(32) DEFAULT '-',             -- 客户端运行版本 (如 v1.1.0)
    app_build VARCHAR(32) DEFAULT '-',               -- 客户端编译指纹
    license_status VARCHAR(32) DEFAULT 'TRIAL',      -- 授权状态 (TRIAL / ACTIVE / EXPIRED / BANNED)
    license_expire VARCHAR(64) DEFAULT '-',          -- 授权到期日 (YYYY-MM-DD 或 PERMANENT)
    remaining_days INTEGER DEFAULT 0,                -- 剩余有效天数 (负数代表逾期)
    customer_name VARCHAR(128) DEFAULT '散户/未登记', -- 客户企业名称
    line_station VARCHAR(128) DEFAULT 'WORKSTATION-01', -- 所在产线/工位编号
    is_virtual_machine INTEGER DEFAULT 0,            -- 是否检测到虚拟机环境 (1:是, 0:否)
    clock_tampered INTEGER DEFAULT 0,                -- 是否检测到本地倒拨时钟作弊 (1:是, 0:否)
    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,   -- 首次上线时间
    last_sync DATETIME DEFAULT CURRENT_TIMESTAMP,    -- 最近心跳同步时间
    sync_count INTEGER DEFAULT 1,                    -- 累计心跳同步次数
    status VARCHAR(20) DEFAULT 'ACTIVE',             -- 运营管控状态 (ACTIVE / BANNED / FROZEN)
    notes TEXT DEFAULT ''                            -- 管理员备注
);

-- 2. 商业授权激活码签发表 (记录由管理员生成的授权 Token 与激活记录)
CREATE TABLE IF NOT EXISTS licenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT NOT NULL UNIQUE,                      -- 生成的 COIL-SEC-... 激活码
    machine_id VARCHAR(64) NOT NULL,                 -- 绑定的目标机器码 (*代表通用通配符)
    plan_type VARCHAR(32) DEFAULT 'TRIAL',           -- 方案类型 (TRIAL_30, QUARTER_90, ANNUAL_365, PERMANENT)
    expire_date VARCHAR(64) NOT NULL,                -- 到期时间字符串 (YYYY-MM-DD 或 PERMANENT)
    customer_name VARCHAR(128) DEFAULT 'ANSV VIP Client', -- 授权客户/公司
    station_id VARCHAR(64) DEFAULT 'WORKSTATION-01', -- 工位代号
    status VARCHAR(32) DEFAULT 'ACTIVE',             -- 状态 (ACTIVE:有效, REVOKED:已吊销, EXPIRED:已过期)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,   -- 签发时间
    activated_at DATETIME,                           -- 客户端首次激活时间
    notes TEXT DEFAULT ''                            -- 商务合作合同/经手人备注
);

-- 3. 软件本体版本发布与 OTA 更新履历表
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

-- 4. 管理员操作审计留痕表 (开通授权、续费延期、拉黑吊销记录)
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action VARCHAR(64) NOT NULL,                     -- 操作行为 (GENERATE_TOKEN, BAN_DEVICE, EXTEND_LICENSE 等)
    target_mid VARCHAR(64) DEFAULT '',               -- 目标机器码
    operator VARCHAR(64) DEFAULT 'ADMIN',            -- 操作人
    details TEXT DEFAULT '',                         -- 操作详情明细
    ip VARCHAR(64) DEFAULT '',                       -- 管理员 IP
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 5. 系统全局键值配置表 (保存全局通告、主推版本与运营参数)
CREATE TABLE IF NOT EXISTS app_config (
    meta_key TEXT PRIMARY KEY,
    meta_value TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 6. 索引优化 (保障百万级查询毫秒响应)
CREATE INDEX IF NOT EXISTS idx_devices_last_sync ON devices(last_sync);
CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
CREATE INDEX IF NOT EXISTS idx_licenses_mid ON licenses(machine_id);
CREATE INDEX IF NOT EXISTS idx_licenses_token ON licenses(token);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);

-- ==============================================================================
-- 初始基准数据注入
-- ==============================================================================

-- 写入当前官方正式发布版本 (v1.1.0)
INSERT OR REPLACE INTO releases (version, build, release_date, download_url, backup_url, sha256, file_size_mb, changelog, is_mandatory, is_active)
VALUES (
    'v1.1.0',
    '20261014_B1',
    '2026-10-20',
    'https://github.com/tonychen5577-tech/coil-architect/releases/download/v1.1.0/ANSV_Coil_Architect_Pro_v1.1.0_20261020_12e1dc6.zip',
    'https://ansv.net/download/coil-architect-v1.1.0.zip',
    '60b84e04a59953c3b3de346d4355baa09eb92ad3deaaf75b3a49c01e6a5e11d8',
    60.60,
    '### ANSV Coil-Architect Pro v1.1.0 商业正式版
- 🌟 全面支持八角形、跑道形(Sensor-Shift)、圆环形与矩形圆角/多边形异形四大微型电磁线圈拓扑；
- ⚡ 毫米级装配空间与目标电阻极速反推求解引擎；
- 🛡️ 磁钢装配气隙 DFM 制造安全红线预警与 ISO 129 截面标注；
- 📊 底部多方案微调数据对比折叠抽屉与 Excel 自适应列宽报表导出；
- 🔑 硬件指纹看门狗与 Cython C 机器码全面加固。',
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
