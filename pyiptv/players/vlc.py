import logging
import os
import signal
import subprocess

from pyiptv.players.base import BasePlayer

logger = logging.getLogger(__name__)


class VLCPlayer(BasePlayer):
    def __init__(self, vlc_path: str = "/usr/bin/cvlc") -> None:
        self.vlc_path = vlc_path
        self.current_process = None

    def play(self, url: str) -> None:
        try:
            # Kill previous VLC process if it exists
            if self.current_process:
                try:
                    os.kill(self.current_process.pid, signal.SIGTERM)
                    self.current_process.wait(
                        timeout=2
                    )  # Wait for process to terminate
                except (ProcessLookupError, subprocess.TimeoutExpired):
                    # Process already dead or not responding, try force kill
                    try:
                        os.kill(self.current_process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass  # Process already terminated
                except Exception as e:
                    logger.debug(f"Error killing previous process: {e}")

            # Start new VLC process and capture it
            self.current_process = subprocess.Popen(
                [self.vlc_path, url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        except Exception as e:
            logger.error(f"Failed to play URL {url} with VLC: {e}")
            # Reset current_process if there was an error
            self.current_process = None

    def stop(self) -> None:
        """Stop the current playback"""
        if self.current_process:
            try:
                os.kill(self.current_process.pid, signal.SIGTERM)
                self.current_process.wait(timeout=2)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.kill(self.current_process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass  # Process already terminated
            except Exception as e:
                logger.debug(f"Error stopping process: {e}")
            finally:
                self.current_process = None

    def __del__(self):
        """Clean up when object is destroyed"""
        self.stop()
