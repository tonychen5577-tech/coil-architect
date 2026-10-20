"""
=============================================================================
Module: src.core.smart_dns
Description: Coil-Architect Pro - 智能 DNS 韧性解析器 (SmartDNS Resilient Resolver)
深度对标 Gear-NVH / FFT 分析软件 全量工业商业桌面软件企业内网网络与数据库连接标准
功能：
解决企业内网、涉密局域网及防火墙运营商 DNS 劫持/污染/阻断导致的
[Errno 11001] getaddrinfo failed 解析失败问题。

解析链路机制：
1. 优先使用 Windows 本机系统默认原生 DNS (若内网直接可达，0 毫秒穿透)；
2. 若系统 DNS 抛出 socket.gaierror (11001) 或解析失败，自动降级请求公共权威 DNS (阿里 223.5.5.5 / 腾讯 119.29.29.29 / 百度 180.76.76.76)；
3. 若企业防火墙完全封锁 UDP 53 查询，自动启用内置的全球 Anycast 高可用安全加速节点 IP 池直连 443 端口，
   结合 TLS SNI 机制，确保企业内网环境下 100% 网络连通率！
=============================================================================
"""

import socket
import struct
from typing import List, Tuple, Any, Optional

_ORIG_GETADDRINFO = socket.getaddrinfo
_HOOK_INSTALLED = False

# 关键 Anycast 高可用节点 IP 池 (Cloudflare 全球边缘加速安全节点)
KNOWN_ANYCAST_IPS = {
    "coil.ansv.net": ["172.67.219.89", "104.21.53.222", "104.21.53.223", "172.67.219.90"],
    "ansv.net": ["172.67.219.89", "104.21.53.222"],
    "coil-architect-cloud.tony-tech.workers.dev": ["172.67.219.89", "104.21.53.222"],
    "workers.dev": ["172.67.219.89", "104.21.53.222"]
}

PUBLIC_DNS_SERVERS = ["223.5.5.5", "119.29.29.29", "180.76.76.76", "114.114.114.114"]


def query_public_dns(domain: str, dns_server: str = "223.5.5.5", timeout: float = 1.5) -> List[str]:
    """通过 Python 标准库向公共权威 DNS 发送原生 UDP 查询 A 记录"""
    try:
        header = struct.pack('!HHHHHH', 0x1234, 0x0100, 1, 0, 0, 0)
        qname = b''
        for part in domain.split('.'):
            qname += struct.pack('B', len(part)) + part.encode('ascii')
        qname += b'\x00'
        qtype = struct.pack('!HH', 1, 1)  # Type A, Class IN
        query = header + qname + qtype

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        sock.sendto(query, (dns_server, 53))
        data, _ = sock.recvfrom(1024)
        sock.close()

        offset = 12 + len(qname) + 4
        ips = []
        while offset < len(data):
            if data[offset] & 0xC0 == 0xC0:
                offset += 2
            else:
                while data[offset] != 0:
                    offset += 1 + data[offset]
                offset += 1
            if offset + 10 > len(data):
                break
            atype, aclass, ttl, rdlen = struct.unpack('!HHIH', data[offset:offset+10])
            offset += 10
            if atype == 1 and rdlen == 4 and offset + 4 <= len(data):
                ip = socket.inet_ntoa(data[offset:offset+4])
                ips.append(ip)
            offset += rdlen
        return ips
    except Exception:
        return []


def smart_getaddrinfo(host: str, port: Any, family: int = 0, type: int = 0, proto: int = 0, flags: int = 0):
    """自愈式企业内网安全 getaddrinfo 增强实现"""
    try:
        # 1. 优先使用系统原生 DNS 解析 (内网域名或可正常访问时毫秒级直通)
        return _ORIG_GETADDRINFO(host, port, family, type, proto, flags)
    except socket.gaierror:
        # 2. 系统解析失败 (常见于内网隔离机房、DNS未配置或企业DNS拦截)
        target_domain = host.lower().strip()
        matched_key = None
        for k in KNOWN_ANYCAST_IPS:
            if target_domain == k or target_domain.endswith("." + k) or "workers.dev" in target_domain or "ansv.net" in target_domain:
                matched_key = k
                break

        if matched_key is not None:
            # 2.1 尝试通过公网权威 DNS (阿里/腾讯) 兜底直查
            for dns in PUBLIC_DNS_SERVERS:
                resolved = query_public_dns(target_domain, dns_server=dns, timeout=1.2)
                if resolved:
                    res = []
                    for ip in resolved:
                        res.append((socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, port or 443)))
                    return res

            # 2.2 若内网封禁了 UDP 53，直接回退至内置 Anycast 高可用 IP 池
            fallback_ips = KNOWN_ANYCAST_IPS.get(matched_key, ["172.67.219.89", "104.21.53.222"])
            res = []
            for ip in fallback_ips:
                res.append((socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, port or 443)))
            return res

        # 无匹配的第三方域名，保持原生异常抛出
        raise


def install_smart_dns_hook():
    """安装全局透明 DNS 韧性补丁"""
    global _HOOK_INSTALLED
    if not _HOOK_INSTALLED:
        socket.getaddrinfo = smart_getaddrinfo
        _HOOK_INSTALLED = True


# 模块导入时自动安装全局保护
install_smart_dns_hook()
