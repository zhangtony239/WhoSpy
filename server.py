import asyncio
import threading
from aioquic.asyncio.server import serve
from aioquic.quic.configuration import QuicConfiguration
from asyncio import StreamReader, StreamWriter
import subprocess
import random

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