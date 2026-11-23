# Run APEX Terminal on Windows

You need Python 3.12 or 3.13, and Node.js 22 LTS. Then open two terminals in this folder, or double-click `start-apex.bat`.

## Install (once)

1. Install Python from https://www.python.org/downloads/ — on the first installer screen, tick **Add python.exe to PATH**.
2. Install Node.js 22 LTS from https://nodejs.org/ — accept the defaults.
3. Close and reopen any Command Prompt or PowerShell windows so they pick up the new PATH.

Or in an admin terminal:

```
winget install Python.Python.3.12
winget install OpenJS.NodeJS.LTS
```

## Start the desk

**Option A — double-click** `start-apex.bat` in this folder. The first run may take a few minutes while it installs packages. Leave the two black windows open. Chrome should open http://127.0.0.1:4317/ — if it does not, paste that address into Chrome yourself.

**Option B — two terminals**

Terminal 1 (API):

```
cd path\to\lawrence-terminal\backend
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8741
```

Terminal 2 (desk):

```
cd path\to\lawrence-terminal\frontend
npm install
npm run dev
```

Then in Chrome on this PC, open http://127.0.0.1:4317/

If Windows asks to allow Python or Node through the firewall, allow it on a private network.

## Use it

Click the command bar at the top (or press `/`), type a ticker such as `AAPL` or `0700.HK`, and press Enter. The tear sheet opens. You can also click a name in the watchlist.

Leave both server windows running. To stop the desk, close those two windows.

## If something fails

- `py` is not recognized: reinstall Python and tick **Add python.exe to PATH**, then open a new terminal. You can also try `python` instead of `py -3`.
- `npm` is not recognized: reinstall Node.js 22 LTS and open a new terminal.
- `pip install` fails (often on `curl_cffi` or `lxml`): install Docker Desktop, then in this folder run `docker compose up --build` and open http://127.0.0.1:4317/
- The page is blank or says the API is unreachable: make sure the backend window is still running on port 8741, then refresh Chrome.
