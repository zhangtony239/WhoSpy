import asyncio
import threading
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
        # 匹配 192.168.x.x, 172.16-31.x.x, 或 172x.x.x
        # 我们这里简化一下，只找 192. 或 172. 开头的，这通常是目标地址
        
        # 匹配 IPv4 地址，且要求是 192. 或 172. 开头的
        # \d{1,3} 匹配 1 到 3 位数字
        ip_pattern = re.compile(r'\b(192\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.\d{1,3}\.\d{1,3}\.\d{1,3})\b')
        
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

class Server:
    def __init__(self):
        self.clients = set()
        self.loop = asyncio.new_event_loop()
        self.ready_event = threading.Event()
        self.stop_future = None
        self.server_transport = None
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self.ready_event.wait() # Wait for server to initialize (get IP, port, etc.)

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._start_server())

    async def _start_server(self):
        # IP Logic
        ip_address = get_local_ip_via_os_command()
        pairCode = '获取失败！'
        if ip_address:
            pairCode = ip_address.split('.')[3].zfill(3)
            pairCode = pairCode + str(random.randint(0, 9))
        
        print(f'房间号: {pairCode}')
        
        self.HOST = "0.0.0.0"
        self.PORT = int("1"+pairCode)
        self.CERTFILE = "cert.pem"
        self.KEYFILE = "key.pem"

        configuration = QuicConfiguration(
            is_client=False,
            alpn_protocols=["h3"],
            idle_timeout=300.0, # 增加超时时间，防止空闲断开
        )
        configuration.load_cert_chain(certfile=self.CERTFILE, keyfile=self.KEYFILE)

        print(f"Starting QUIC server on {self.HOST}:{self.PORT}")
        
        # Signal ready
        self.ready_event.set()

        self.server_transport = await serve(
            host=self.HOST,
            port=self.PORT,
            configuration=configuration,
            stream_handler=self._stream_handler,
        )
        
        self.stop_future = asyncio.Future()
        await self.stop_future
        
        # Cleanup
        self.server_transport.close()
        print("Server stopped.")

    def _stream_handler(self, reader: StreamReader, writer: StreamWriter):
        asyncio.create_task(self._handle_stream(reader, writer))

    async def _handle_stream(self, reader: StreamReader, writer: StreamWriter):
        peername = writer.get_extra_info('peername')
        #print(f"✅ New stream established from {peername}")
        self.clients.add(writer)
        try:
            while True:
                data = await reader.read(1024)
                if not data:
                    print(f"Client {peername} disconnected (EOF).")
                    break
                #message = data.decode()
                #print(f"👂 Received from {peername}: {message}")
        except Exception as e:
            print(f"❌ Error during stream handling for {peername}: {e}")
        finally:
            self.clients.discard(writer)
            print(f"Stream closed for {peername}. Remaining clients: {len(self.clients)}")

    def send(self, message):
        if not self.clients:
            print("No clients connected.")
            return
        print(f"Broadcasting to {len(self.clients)} clients: {message}")
        asyncio.run_coroutine_threadsafe(self._broadcast(message), self.loop)

    async def _broadcast(self, message):
        for writer in list(self.clients):
            try:
                writer.write(message.encode())
                # await writer.drain() 
            except Exception as e:
                print(f"Failed to send to client: {e}")
                self.clients.discard(writer)

    def stop(self):
        """Stop the server and close all connections."""
        if self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._stop(), self.loop)
            self.thread.join(timeout=2)

    async def _stop(self):
        print("Stopping server...")
        # Close all client connections
        for writer in list(self.clients):
            try:
                writer.close()
            except:
                pass
        self.clients.clear()
        
        # Stop the server loop
        if self.stop_future and not self.stop_future.done():
            self.stop_future.set_result(True)

if __name__ == "__main__":
    s = Server()
    try:
        while True:
            cmd = input("Enter message to broadcast (or 'q' to quit): ")
            if cmd == 'q':
                break
            s.send(cmd)
    except KeyboardInterrupt:
        print("\nServer shutting down.")
    finally:
        s.stop()