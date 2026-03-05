import os
import pty
import fcntl
import asyncio
import json
import termios
import struct
import shlex
import sys
import threading
import http.server
import socketserver

try:
    import websockets
except ImportError:
    print("The 'websockets' library is missing. Install it with: pip3 install websockets")
    sys.exit(1)

# Keep track of active PTY pairs
async def handle_client(websocket):
    # Create pseudo-terminal (PTY)
    master_fd, slave_fd = pty.openpty()
    
    # Spawn the bash process
    pid = os.fork()
    if pid == 0:
        # Child process: configure terminal and launch bash
        os.setsid()
        os.dup2(slave_fd, 0)
        os.dup2(slave_fd, 1)
        os.dup2(slave_fd, 2)
        
        # Close file descriptors
        if master_fd > 2:
            os.close(master_fd)
        if slave_fd > 2:
            os.close(slave_fd)
            
        # Set environment variables for the terminal
        env = os.environ.copy()
        env['TERM'] = 'xterm-256color'
        
        # Execute bash
        os.execvpe('bash', ['bash', '-l'], env)
    
    # Parent process: interact with the spawned bash
    os.close(slave_fd)

    def set_winsize(fd, row, col):
        # Update the PTY window size when the browser window is resized
        winsize = struct.pack("HHHH", row, col, 0, 0)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
    
    loop = asyncio.get_running_loop()
    
    async def pty_to_ws():
        # Read terminal output from PTY and send it to the WebSocket
        while True:
            try:
                # 4096 bytes read
                data = await loop.run_in_executor(None, os.read, master_fd, 4096)
                if not data:
                    break
                # Websockets accepts strings or bytes. We send bytes for binary stability.
                await websocket.send(data)
            except OSError:
                break
            except websockets.exceptions.ConnectionClosed:
                break
                
    async def ws_to_pty():
        # Read input from the WebSocket and write it to the PTY
        try:
            async for message in websocket:
                if isinstance(message, str):
                    try:
                        cmd = json.loads(message)
                        if cmd.get('type') == 'resize':
                            set_winsize(master_fd, cmd['rows'], cmd['cols'])
                    except json.JSONDecodeError:
                        os.write(master_fd, message.encode('utf-8'))
                else: 
                    # Binary data (standard keyboard input)
                    os.write(master_fd, message)
        except websockets.exceptions.ConnectionClosed:
            pass
            
    # Run both data directions concurrently
    try:
        await asyncio.gather(pty_to_ws(), ws_to_pty())
    finally:
        # Cleanup when the WebSocket connection is closed
        os.close(master_fd)
        # Terminate bash process
        try:
            os.kill(pid, 9)
            os.waitpid(pid, 0)
        except ProcessLookupError:
            pass

async def main():
    # 1. Start a simple HTTP server in a background thread to serve index.html
    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            pass # suppress HTTP logs

    def start_http():
        with socketserver.TCPServer(("", 8000), Handler) as httpd:
            print("UI Web Server running on http://0.0.0.0:8000")
            httpd.serve_forever()

    threading.Thread(target=start_http, daemon=True).start()

    # 2. Start the WebSocket server on port 8765
    print("WebSocket Server running on ws://0.0.0.0:8765")
    async with websockets.serve(handle_client, "0.0.0.0", 8765):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
