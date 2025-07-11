import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import os

class ReloadHandler(FileSystemEventHandler):
    def __init__(self):
        self.process = None
        self.start_bot()

    def start_bot(self):
        if self.process:
            self.process.kill()
        print("🔁 Starting bot...")
        self.process = subprocess.Popen(["python", "src/bot.py"])  # adjust if your main is somewhere else

    def on_any_event(self, event):
        if event.src_path.endswith(".py"):
            print("🔁 Code changed, reloading bot...")
            self.start_bot()

if __name__ == "__main__":
    path = "src"
    event_handler = ReloadHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    print("🔍 Watching for file changes in 'src/'...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
