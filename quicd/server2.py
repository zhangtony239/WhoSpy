import subprocess
import threading
import asyncio
import random

def getIpcfg():
    result = subprocess.run(
        'ipconfig',
        capture_output=True,
        text=True
    )
    output = result.stdout
    print(output)

    output = output.split('\n')
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
        self.thread = threading.Thread(
            target=self._run_loop,
            daemon=True
        )
        self.thread.start()
        self.ready_event.wait()

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.)
    
    async def _start_server(self):
        ipAddress = getIpcfg()
        pairCode = '获取失败！'
        if ipAddress:
            pairCode = ipAddress.split('.')[3].zfill(3)
            pairCode = pairCode + str(random.randint(0, 9))
        
        print(f'房间号: {pairCode}')

        self.HOST = "0.0.0.0"
        self.PORT = int("1"+pairCode)
        self.CERTFILE = "cert.pem"
        self.KEYFILE = "key.pem"

if __name__ == '__main__':
    print(getIpcfg())