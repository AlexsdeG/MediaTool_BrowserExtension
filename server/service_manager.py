### 

import sys
import time
import win32serviceutil
import win32service
import win32event
import servicemanager
import threading
from pathlib import Path

# Add your app directory to path
sys.path.append(str(Path(__file__).parent))

from service import app, socketio

class MediaToolService(win32serviceutil.ServiceFramework):
    _svc_name_ = "MediaToolService"
    _svc_display_name_ = "MediaTool Local Service"
    _svc_description_ = "Local service for MediaTool browser extension"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.is_alive = True

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.is_alive = False

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        
        # Start the Flask-SocketIO server in a separate thread
        server_thread = threading.Thread(
            target=lambda: socketio.run(
                app, 
                host='127.0.0.1', 
                port=8765, 
                debug=False,
                use_reloader=False
            ),
            daemon=True
        )
        server_thread.start()

        # Wait for stop signal
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(MediaToolService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(MediaToolService)