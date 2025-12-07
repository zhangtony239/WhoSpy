import asyncio
import ssl
from aioquic.asyncio.client import connect
from aioquic.quic.configuration import QuicConfiguration
import subprocess

def get_local_ip_via_os_command():
    result = subprocess.run(
        'ipconfig',
        capture_output=True,
        text=True
    )
    output = result.stdout.split('\n')
    ips = []
    skipping = False
    for line in output:
        if skipping and len(line.split('适配器')) > 1:
            skipping = False
            continue
        if skipping:
            continue
        if len(line.split('tun')) > 1:
            skipping = True
            continue
        if 'IPv4' in line:
            ip = line.split(':')[1].strip()
            ips.append(ip)
    
    return ips[0]

# 调用函数并打印结果
ip_address = get_local_ip_via_os_command()
if ip_address:
    ip_address = ip_address.split('.') # type: ignore
    ip_address.pop()
    ip_address = '.'.join(ip_address)
else:
    print("Warning: Could not determine local IP. Assuming localhost for testing.")
    ip_address = "127.0.0" # Fallback

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
        idle_timeout=300.0, # 增加超时时间
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

            # 4. 发送初始数据 (必须发送数据以触发服务器的 stream_handler)
            message = "Hello from client!"
            writer.write(message.encode())
            print(f"➡️ Sent: {message}")
            
            # 5. 持续接收响应
            try:
                while True:
                    data = await reader.read(1024)
                    if not data:
                        print("Server closed the stream.")
                        break
                    response = data.decode()
                    print(f"👂 Received: {response}")
            except asyncio.CancelledError:
                print("Connection cancelled.")
            except Exception as e:
                print(f"Stream error: {e}")
            finally:
                # 7. 关闭流
                writer.close()
                print("✅ Stream closed.")

    except Exception as e:
        print(f"❌ Connection error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(run_client())
    except KeyboardInterrupt:
        print("\nClient shutting down.")