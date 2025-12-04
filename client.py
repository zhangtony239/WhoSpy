import asyncio
import ssl
from aioquic.asyncio.client import connect
from aioquic.quic.configuration import QuicConfiguration

import subprocess
import platform
import re

def get_local_ip_via_os_command():
    """
    通过调用系统命令（ipconfig/ip addr）并解析输出来获取本地局域网 IP。
    这个方法在复杂的网络环境中通常更精确。
    """
    system = platform.system()
    command = []
    
    if system == "Windows":
        # Windows 系统使用 ipconfig
        command = ["ipconfig"]
        # Windows 的输出是 GBK 或其它编码，需要指定解码
        encoding = 'cp936' # 或 'gbk'
    elif system == "Linux" or system == "Darwin": # Darwin 是 macOS 的内核名
        # Linux/macOS 使用 ip addr
        command = ["ip", "addr"]
        encoding = 'utf-8'
    else:
        print(f"不支持的操作系统: {system}")
        return None

    try:
        # 1. 执行系统命令
        # text=True 相当于 universal_newlines=True，用于自动解码输出，但有时编码会错
        # 显式指定 encoding 更可靠
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding=encoding,
            check=True
        )
        output = result.stdout
        
        # 2. 正则表达式匹配私有 IP 地址
        # 匹配 192.168.x.x, 172.16-31.x.x, 或 10.x.x.x
        # 我们这里简化一下，只找 192. 或 10. 开头的，这通常是目标地址
        
        # 匹配 IPv4 地址，且要求是 192. 或 10. 开头的
        # \d{1,3} 匹配 1 到 3 位数字
        ip_pattern = re.compile(r'\b(192\.\d{1,3}\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3})\b')
        
        # 3. 查找所有匹配的 IP
        matches = ip_pattern.findall(output)
        
        if matches:
            # 返回找到的第一个匹配项 (通常就是活跃的局域网 IP)
            return matches[0]
        else:
            print("解析失败: 未找到 192.x.x.x 或 10.x.x.x 开头的 IP 地址。")
            return None

    except subprocess.CalledProcessError as e:
        print(f"命令执行失败: {e.stderr}")
        return None
    except FileNotFoundError:
        print(f"命令未找到: 确保 {command[0]} 在您的系统 PATH 中。")
        return None
    except Exception as e:
        print(f"发生其他错误: {e}")
        return None

# 调用函数并打印结果
ip_address = get_local_ip_via_os_command()
ip_address = ip_address.split('.') # type: ignore
ip_address.pop()
ip_address = '.'.join(ip_address)

while True:
    pairCode = input("请输入4位房间号：")
    if len(pairCode) == 4:
        break
ip3 = pairCode[:-1]
for i in ip3:
    if i == '0':
        ip3 = ip3[1:]
    else:
        break

# 替换为你的服务器的局域网 IP 地址
SERVER_HOST = f"{ip_address}.{ip3}"  # 示例: 假设服务器 IP 是这个
SERVER_PORT = int("1"+pairCode)
# 服务器的 Server Name Indication (SNI)，必须和证书中的 CN/subjectAltName 匹配
SERVER_NAME = "localhost" 

async def run_client():
    # 1. 配置 QUIC
    configuration = QuicConfiguration(
        is_client=True,
        alpn_protocols=["h3"], # 必须和服务器配置一致
        server_name=SERVER_NAME,
        # **重要：** 由于是自签名证书，我们在这里禁用证书验证。
        # 在生产环境中，应该提供 ca_certs 来验证服务器证书。
        verify_mode=ssl.CERT_NONE, 
    )

    print(f"Attempting to connect to {SERVER_HOST}:{SERVER_PORT}")
    try:
        # 2. 连接服务器
        async with connect(
            host=SERVER_HOST,
            port=SERVER_PORT,
            configuration=configuration,
        ) as protocol:
            print("🚀 Connection established.")
            
            # 3. 创建一个双向流
            reader, writer = await protocol.create_stream()

            # 4. 发送数据
            message = "Hello from aioquic client!"
            writer.write(message.encode())
            print(f"➡️ Sent: {message}")
            
            # 5. 通知服务器发送完毕并关闭发送侧
            writer.write_eof()
            await writer.drain()

            # 6. 接收响应
            data = await reader.read(65535)
            response = data.decode()
            print(f"👂 Received: {response}")
            
            # 7. 关闭流
            writer.close()
            print("✅ Stream closed.")

    except Exception as e:
        print(f"❌ Connection error: {e}")

if __name__ == "__main__":
    asyncio.run(run_client())