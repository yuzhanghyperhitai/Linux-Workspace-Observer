"""Shell Hook data receiver for LWO."""

import asyncio
import json
import os
import time
from typing import Dict, Any

from lwo.config import get_config
from lwo.storage.database import get_database
from lwo.processors.sanitizer import Sanitizer
from lwo.utils.logger import setup_logger

logger = setup_logger(__name__)


class ShellHookReceiver:
    """Receive and process shell command data from Unix socket."""
    
    def __init__(self):
        """Initialize shell hook receiver."""
        self.config = get_config()
        self.db = get_database()
        self.sanitizer = Sanitizer()
        
        # Git context collector
        from lwo.collectors.git_context import GitContextCollector
        self.git_collector = GitContextCollector()
        
        # Unix socket path
        self.socket_path = self.config.data_dir / 'shell.sock'
        
        # Remove existing socket if it exists
        if self.socket_path.exists():
            self.socket_path.unlink()
        
        self.server = None
    
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle incoming client connection.
        
        Args:
            reader: Stream reader
            writer: Stream writer
        """
        try:
            # Read data from client
            data = await reader.read(4096)
            if not data:
                return
            
            # Parse JSON data
            try:
                command_data = json.loads(data.decode('utf-8'))
                await self.process_command(command_data)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON data: {e}")
        
        except Exception as e:
            logger.error(f"Error handling client: {e}")
        
        finally:
            writer.close()
            await writer.wait_closed()
    
    async def process_command(self, data: Dict[str, Any]):
        """Process shell command data.
        
        Args:
            data: Command data dict with keys: command, pwd, ts, duration, exit_code
        """
        try:
            command = data.get('command', '')
            pwd = data.get('pwd', '')
            ts = data.get('ts', int(time.time()))
            duration = data.get('duration', 0.0)
            exit_code = data.get('exit_code', 0)
            
            # Sanitize command
            sanitized_command = self.sanitizer.sanitize_command(command)
            
            # Insert into database
            self.db.insert_shell_command(
                command=command,
                sanitized_command=sanitized_command,
                pwd=pwd,
                ts=ts,
                duration=duration,
                exit_code=exit_code
            )
            
            # Check Git context on PWD change
            self.git_collector.on_pwd_change(pwd)
            
            logger.debug(f"Recorded command: {sanitized_command} (exit={exit_code})")
        
        except Exception as e:
            logger.error(f"Failed to process command data: {e}")
    
    async def start(self):
        """Start the Unix socket server."""
        try:
            # Create Unix socket server
            self.server = await asyncio.start_unix_server(
                self.handle_client,
                path=str(self.socket_path)
            )
            
            # Set socket permissions to allow user access
            os.chmod(self.socket_path, 0o600)
            
            logger.info(f"Shell Hook receiver started on {self.socket_path}")
            
            async with self.server:
                await self.server.serve_forever()
        
        except Exception as e:
            logger.error(f"Failed to start Shell Hook receiver: {e}")
            raise
    
    async def stop(self):
        """Stop the Unix socket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("Shell Hook receiver stopped")
        
        # Clean up socket file
        if self.socket_path.exists():
            self.socket_path.unlink()


async def run_shell_hook_receiver():
    """Run the shell hook receiver."""
    receiver = ShellHookReceiver()
    await receiver.start()


if __name__ == '__main__':
    asyncio.run(run_shell_hook_receiver())
