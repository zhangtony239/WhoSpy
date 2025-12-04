import asyncio
from aioquic.asyncio.server import serve
from aioquic.quic.configuration import QuicConfiguration
from asyncio import StreamReader, StreamWriter
import subprocess
import platform
import re
import random

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

pairCode = '获取失败！'
if ip_address:
    pairCode = ip_address.split('.')[3].zfill(3)
    pairCode = pairCode + str(random.randint(0, 9))

print(f'房间号: {pairCode}')

# 服务器地址和端口
HOST = "0.0.0.0"  # 监听所有接口，用于局域网连接
PORT = int("1"+pairCode)
CERTFILE = "cert.pem"  # 你的证书文件
KEYFILE = "key.pem"    # 你的私钥文件

async def stream_handler(reader: StreamReader, writer: StreamWriter):
    """处理新传入的 QUIC 流"""
    peername = writer.get_extra_info('peername')
    print(f"✅ New stream established from {peername}")

    try:
        # 1. 接收数据
        data = await reader.read(65535)
        message = data.decode()
        print(f"👂 Received: {message}")

        # 2. 发送响应
        response = f"Hello, Client! Your message was: {message}"
        writer.write(response.encode())
        
        # 3. 关闭流 (FIN)
        await writer.drain()
        writer.write_eof()
        print("➡️ Response sent and stream closed.")

    except Exception as e:
        print(f"❌ Error during stream handling: {e}")
    finally:
        writer.close()

async def main():
    # 1. 配置 QUIC
    configuration = QuicConfiguration(
        is_client=False,
        alpn_protocols=["h3"],  # 任意应用层协议标识符
    )
    configuration.load_cert_chain(certfile=CERTFILE, keyfile=KEYFILE)

    # 2. 启动服务器
    print(f"Starting QUIC server on {HOST}:{PORT}")
    await serve(
        host=HOST,
        port=PORT,
        configuration=configuration,
        stream_handler=stream_handler,  # 传入流处理函数 # type: ignore
    )
    
    # 3. 保持运行
    await asyncio.Future() # 永远等待，保持服务器运行

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer shutting down.")