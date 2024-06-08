import React, { useEffect, useState } from 'react';

class WebSocketService {

    constructor() {
      this.socket = null;
      this.messageHandlers = [];
      this.cleanupHandlers = [];
      this.closing = false;
      this.connected = false;
      this.connecting = false;
      this.connectionAddress = null;
      this.syncToken = null;
    }
  
    connect(url, callback) {

        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            console.error('WebSocketService: Already connected');
            return;
        }

        if (this.connecting) {
            console.error('WebSocketService: You are already trying to connect');
            return;
        }

        this.connectionAddress = url;

        this.connecting = true;
        this.socket = new WebSocket(url);
        this.socket.onmessage = this.handleMessage;
        this.socket.onopen = () => {

          if (this.retryConnecting) {
            if (this.retryHandlingCallback) {
              this.retryHandlingCallback(-1);
            }
          }

          this.retryConnecting = false;
          this.connected = true;
          this.connecting = false;
          this.retryCount = 0;
          callback()
        };

        this.socket.onclose = () => {
            this.connecting = false;
            if (!this.connected) {
              alert("Connection to server failed. Can't reach the backend.");
              return;
            }

            console.log('WebSocketService: Connection broken!');
            if (this.retryCount < 30) {

              if (this.retryHandlingCallback) {
                this.retryHandlingCallback(this.retryCount);
              }

              this.retryConnecting = true;
              setTimeout(() => {
                this.retryCount++;
                this.connect(url, () => {
                  this.sendMessage({
                    type: "register", 
                    action: "resync",
                    sync_token: this.syncToken
                  });
                });
              }, 5000);
            } else {
              this.retryConnecting = false;
              this.closing = true;
              console.log('WebSocketService: Connection closed');
              console.log('WebSocketService: Cleaning up message handlers', this.cleanupHandlers.length);
              this.cleanupHandlers.forEach(handler => handler.callback());
              //this.cleanupHandlers = [];
              console.log('WebSocketService: Cleaned up!');
            }

        }
    }
  
    handleMessage = (event) => {
        const message = JSON.parse(event.data);
        const { type } = message;

        console.log('WebSocketService: Received message', message);
        console.log(this.messageHandlers)

        if (type === "sync_token") {
          this.syncToken = message.msg;
          console.log("Sync Token received: ", this.syncToken);
          return;
        }

        // Filter message handlers by type and call matching handlers
        this.messageHandlers
          .filter(handler => handler.messageType === type)
          .forEach(handler => handler.callback(message));
      };
    
    addCleanUpHandler(handler) {
      if (this.closing)
        return;
      if (this.cleanupHandlers.find(h => h.identifier === handler.identifier))
        return;

      this.cleanupHandlers.push(handler);
    }

    addMessageHandler(handler) {

      // check if handler already is registered and updating it. checking via handler.identifier
      
      if (handler.identifier !== undefined) {
        const existingHandler = this.messageHandlers.find(h => h.identifier === handler.identifier);
        if (existingHandler) {
          this.removeMessageHandler(existingHandler);
          this.messageHandlers.push(handler);
          return;
        }
      }

      this.messageHandlers.push(handler);
    }
    
    removeMessageHandler(handler) {
      this.messageHandlers = this.messageHandlers.filter(h => h !== handler);
    }

    sendMessage(message) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            console.log('WebSocketService: Sending message', message);
            this.socket.send(JSON.stringify(message));
        }
    }
  
    close() {
      if (this.socket) {
        this.socket.close();
        this.messageHandlers = this.messageHandlers.filter(handler => handler.persist !== undefined && handler.persist === true)
      }
    }
  }
  
  export default WebSocketService;