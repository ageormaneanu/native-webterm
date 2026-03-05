# Native WebTerm

A lightweight, dependency-free web-based terminal that cross-compiles natively for Linux and Android.

**Architecture**
- **Client:** The browser UI is [index.html](index.html). It uses `xterm.js` to render a terminal and a WebSocket connection to the backend.
- **Server (Go):** `main.go` hosts a static HTTP server for the UI and a WebSocket endpoint `/ws`. It spawns a local shell attached to a PTY (via `github.com/creack/pty`) and proxies PTY <-> WebSocket data.
- **Alternative server (Python):** `server.py` provides the same behavior using `pty` + `websockets` and can run on devices where Python/Termux is preferred.
- **Protocol:** Binary messages carry terminal I/O. Text JSON messages are used for control events (e.g. `{ "type":"resize", "cols":80, "rows":24 }`).

**Implementation Notes**
- **Files:** Key sources are `main.go` (Go server), `index.html` (client UI), and `server.py` (Python server alternative).
- **Dependencies:** Go: `github.com/creack/pty`, `github.com/gorilla/websocket` (declared in `go.mod`). Python server requires `websockets` when used.
- **PTY handling:** The Go server starts a shell under a PTY and streams reads/writes. Resize messages call `pty.Setsize` to update terminal dimensions.
- **Cross-compile quirks:** Building for `android/arm` can require cgo (NDK) because some module files reference `import "C"`. Building for `android/arm64` can succeed with `CGO_ENABLED=0` as shown in the repo.

**Deployment (ADB / Android device)**
- **Prerequisites:** `adb` installed, USB debugging enabled on device, device visible in `adb devices`.
- **Fast build (recommended):**
```bash
./scripts/build_android.sh
```
- **Build on host (example for arm64):**
```bash
# from project root
GOOS=android GOARCH=arm64 CGO_ENABLED=0 go build -v -o webterm-android-arm64 main.go
```
- **Push binary + UI to device (example for device `alina_4100`):**
```bash
# adopt the device serial if multiple devices are connected
adb -s alina_4100 push webterm-android-arm64 /data/local/tmp/webterm
adb -s alina_4100 push index.html /data/local/tmp/index.html
adb -s alina_4100 shell chmod 755 /data/local/tmp/webterm
```
- **Start server on device (background) and capture logs:**
```bash
# start in background and write logs to /data/local/tmp/webterm.log
adb -s alina_4100 shell "cd /data/local/tmp && nohup ./webterm 8000 >/data/local/tmp/webterm.log 2>&1 & echo $!"
```
- **Make the device port accessible from host:**
```bash
# reverse host:device port so host can open http://localhost:8000
adb -s alina_4100 reverse tcp:8000 tcp:8000
```
- **Access UI:** Open `http://localhost:8000` on your host machine (or `http://127.0.0.1:8000`).
- **Logs / control:**
```bash
# view logs
adb -s alina_4100 shell tail -f /data/local/tmp/webterm.log
# stop server
adb -s alina_4100 shell pkill webterm
```

**On-device build (Termux) fallback**
- If cross-compiling is not desired, install Termux and build there:
```bash
# on device (Termux)
pkg install git golang
git clone <repo>
cd native-webterm
go build -v -o webterm main.go
./webterm 8000
```

**Troubleshooting & Tips**
- **Permissions:** Use `/data/local/tmp` (commonly executable) or Termux home if `exec` fails.
- **cgo / NDK:** If you must build `GOARCH=arm` and encounter "requires external (cgo) linking": install Android NDK and set appropriate `CC` to the NDK clang, or prefer the device/Termux build.
- **WebSocket origin:** The client opens `/ws` on same host; if you expose the device via a network address, ensure the page and WebSocket use the same origin or update the server config accordingly.
- **Security:** This project exposes a shell — avoid running untrusted builds on public networks. Use local-only access (ADB reverse) or add authentication and TLS if exposing beyond localhost.

For quick reference, see `main.go`, `index.html`, and `server.py` in the repository root.
