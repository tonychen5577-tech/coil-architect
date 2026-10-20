# ☁️ Cloudflare 边缘分布式授权管理后台部署指南 (3分钟极速上线)

Cloudflare 提供了完全免费的全球边缘计算网络 (**Workers**) 与分布式边缘 SQLite 数据库 (**D1**)。  
每天提供 **100,000 次免费请求** 与 **5,000,000 次数据库读取**，对于工业微型执行器软件的日常商业授权、工位机心跳监测与 OTA 发版使用完全是 **永久免费** 的。

---

## 方式一：网页控制台极速部署（推荐，全图形化鼠标操作，3分钟完成）

无需在本地安装任何 Node.js 或命令行工具，推荐直接在 **Cloudflare 网页控制台** 操作：

### 第一步：创建免费的 D1 数据库
1. 打开并登录 [Cloudflare 控制台](https://dash.cloudflare.com/)；
2. 在左侧菜单栏点击 **「存储与数据库 (Storage & Databases)」** -> **「D1 SQL 数据库」**；
3. 点击 **「创建 (Create)」**，数据库名称输入：`coil_architect_db`，点击创建；
4. 进入刚刚创建的 `coil_architect_db`，点击顶部的 **「控制台 (Console)」** 选项卡；
5. 打开本项目中的 [`server_cloudflare/schema.sql`](file:///c:/Workspace/07_AI_Work/coil-architect/server_cloudflare/schema.sql)，全选复制里面的 SQL 内容；
6. 粘贴到控制台中，点击 **「执行 (Execute)」**。此时 5 张数据表与索引已在 Cloudflare 全球边缘节点瞬间初始化完成！

---

### 第二步：创建 Worker 并绑定 D1 数据库
1. 在左侧菜单栏点击 **「Workers 和 Pages」** -> 点击 **「创建应用程序 (Create application)」**；
2. 选择 **「创建 Worker」**，名称可以起为：`coil-architect-cloud`（或任意名称），点击 **「部署 (Deploy)」**；
3. 部署成功后，点击进入该 Worker，点击 **「设置 (Settings)」** -> **「变量与绑定 (Variables and Bindings)」**；
4. 找到 **「D1 数据库绑定 (D1 Database Bindings)」**，点击 **「添加绑定 (Add binding)」**：
   - **变量名称 (Variable name)**：必须填大写的 `DB`；
   - **D1 数据库 (D1 Database)**：下拉选择第一步创建的 `coil_architect_db`；
   - 点击 **「保存并部署 (Save and deploy)」**。

---

### 第三步：粘贴代码并上线发布
1. 回到该 Worker 的主页面，点击右上角的 **「编辑代码 (Edit Code)」**；
2. 打开本项目中的 [`server_cloudflare/worker.js`](file:///c:/Workspace/07_AI_Work/coil-architect/server_cloudflare/worker.js)，全选复制；
3. 将左侧默认的 JavaScript 代码全部清空，粘贴进复制的 `worker.js` 代码；
4. 点击右上角的 **「保存并部署 (Deploy)」**！

---

### 第四步：测试与验证

🎉 **大功告成！您现在拥有专属的商业管理平台：**

1. **测试普通访客访问**：
   - 在浏览器打开您的 Worker 域名（例如 `https://coil-architect-cloud.xxx.workers.dev/`）；
   - 页面会**自动 302 重定向**跳转到您的官网 [ansv.net](https://ansv.net)，外界访客完全看不到管理后台！
2. **测试管理员后台登录**：
   - 在浏览器访问：`https://coil-architect-cloud.xxx.workers.dev/admin`；
   - 弹出深蓝工业级安全鉴权界面，输入默认管理员密码：
     ```text
     Ansv@Coil#2026
     ```
   - 解锁进入 **ANSV Coil-Architect Pro 商业授权与工位监控控制台**！
3. **测试一键生成商业激活码**：
   - 点击 **【➕ 为客户一键生成激活码】**；
   - 输入测试机器码（如 `COIL-609D-64D4-5D11-35E2`），选择方案（如“🟢 30天项目评估版”），点击“立即生成”；
   - 秒级生成与客户端 100% 互通的加密 Token（如 `COIL-SEC-...`），并可一键复制微信回复模板直接发给客户！

---

## 方式二：Wrangler 命令行自动化部署（进阶开发者）

如果您习惯使用命令行，也可以在本地一键发布：

```bash
cd c:\Workspace\07_AI_Work\coil-architect\server_cloudflare

# 1. 登录 Cloudflare
npx wrangler login

# 2. 创建 D1 数据库
npx wrangler d1 create coil_architect_db
# (将终端输出的 database_id 填入 wrangler.toml 中的 YOUR_D1_DATABASE_ID)

# 3. 初始化数据表
npx wrangler d1 execute coil_architect_db --file=./schema.sql --remote

# 4. 发布上线
npx wrangler deploy
```

---

## 🌐 进阶可选：绑定自定义专属域名 (如 `coil.ansv.net`)

如果您的 `ansv.net` 域名托管在 Cloudflare 上：
1. 进入 Worker -> **「设置 (Settings)」** -> **「触发器与域 (Triggers & Domains)」**；
2. 点击 **「添加自定义域 (Add Custom Domain)」**；
3. 输入二级域名：`coil.ansv.net`，点击添加；
4. Cloudflare 会自动申请全球 SSL 证书，10 秒内即可通过 `https://coil.ansv.net/admin` 直达管理控制台！
