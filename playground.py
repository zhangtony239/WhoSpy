from server import Server
import time

if __name__ == '__main__':
    h3d = Server()
    
    # Give some time for server to start and print room code
    time.sleep(1) 
    
    h3d.send('hi')
    
    # Keep the main thread alive to allow server thread to run
    try:
        while True:
            cmd = input("Enter message to broadcast (or 'q' to quit): ")
            if cmd == 'q':
                break
            h3d.send(cmd)
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        h3d.stop()