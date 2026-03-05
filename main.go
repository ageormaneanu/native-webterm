package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
	"os/exec"
	"runtime"
	"sync"

	"github.com/creack/pty"
	"github.com/gorilla/websocket"
)

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		return true // Allow all origins for local terminal
	},
}

type WindowSize struct {
	Type string `json:"type"`
	Cols uint16 `json:"cols"`
	Rows uint16 `json:"rows"`
}

func handleWebsocket(w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Println("Upgrade error:", err)
		return
	}
	defer conn.Close()

	// Determine which shell to use based on OS
	shell := "sh"
	if runtime.GOOS == "linux" {
		if _, err := os.Stat("/bin/bash"); err == nil {
			shell = "bash"
		}
	} else if runtime.GOOS == "android" {
		shell = "/system/bin/sh"
	}

	cmd := exec.Command(shell)
	
	// Start the command with a pty.
	ptmx, err := pty.Start(cmd)
	if err != nil {
		log.Println("Failed to start pty:", err)
		return
	}
	defer func() { _ = ptmx.Close() }() // Best effort.

	var wg sync.WaitGroup
	wg.Add(2)

	// Read from PTY and write to WebSocket
	go func() {
		defer wg.Done()
		buf := make([]byte, 4096)
		for {
			n, err := ptmx.Read(buf)
			if err != nil {
				log.Println("PTY read error:", err)
				return
			}
			if err := conn.WriteMessage(websocket.BinaryMessage, buf[:n]); err != nil {
				log.Println("WebSocket write error:", err)
				return
			}
		}
	}()

	// Read from WebSocket and write to PTY
	go func() {
		defer wg.Done()
		for {
			messageType, p, err := conn.ReadMessage()
			if err != nil {
				log.Println("WebSocket read error:", err)
				return
			}
			
			if messageType == websocket.TextMessage {
				// Try to parse as JSON for resize events
				var winSize WindowSize
				if err := json.Unmarshal(p, &winSize); err == nil && winSize.Type == "resize" {
					_ = pty.Setsize(ptmx, &pty.Winsize{
						Rows: winSize.Rows,
						Cols: winSize.Cols,
					})
					continue
				}
			}

			// Write standard input to PTY
			_, err = ptmx.Write(p)
			if err != nil {
				log.Println("PTY write error:", err)
				return
			}
		}
	}()

	wg.Wait()
}

func main() {
	port := "8000"
	if len(os.Args) > 1 {
		port = os.Args[1]
	}

	http.Handle("/", http.FileServer(http.Dir(".")))
	http.HandleFunc("/ws", handleWebsocket)

	log.Printf("Server started on http://0.0.0.0:%s\n", port)
	err := http.ListenAndServe("0.0.0.0:"+port, nil)
	if err != nil {
		log.Fatal("ListenAndServe: ", err)
	}
}
