import React, { useEffect, useState } from 'react';

class SSEService {
  constructor() {
    this.eventSource = null;
    this.messageHandlers = [];
    this.cleanupHandlers = [];
    this.closing = false;
    this.connected = false;
    this.connecting = false;
    this.connectionAddress = null;
    this.syncToken = null;
    this.skipRetry = false;

    this.token = null;
    this.registration_token = null;

  }

  connect(url) {

    if (url === undefined) {
      url = '/dnd/backend/register'; // only currently for testing purposes
    }

    if (this.eventSource) {
      console.error('SSEService: Already connected');
      return;
    }

    if (!this.registration_token) {
      console.error('SSEService: No registration token');
      return;
    }

    this.eventSource = new EventSource(url + "/" + this.registration_token);
    
    //this.eventSource.onmessage = this.handleMessage;
    
    this.messageHandlers.forEach(handler => {
      this.eventSource.addEventListener(handler.messageType, handler.callback);
    });

    this.eventSource.onerror = (error) => {
      console.error('SSEService: Error connecting to server', error);
    };

    console.log('SSEService: Connected to server');
  }

  handleMessage = (event) => {
    console.log('SSEService: Received event:', event);
    const message = JSON.parse(event.data);
    console.log('SSEService: Received message:', message);

    // get event type
    const type = message.type;

    
    this.messageHandlers
      .filter(handler => handler.messageType === type)
      .forEach(handler => handler.callback(message));
  };

  addCleanUpHandler(handler) {

  }

  addMessageHandler(handler) {
    this.messageHandlers.push(handler);
  }

  removeMessageHandler(handler) {
    this.messageHandlers = this.messageHandlers.filter(h => h !== handler);
  }

  sendMessage(message, callback, suppressMessageHandlers) {
    // Send Message via a post request to /backend/action (non blocking), then wait for a response
    // If the response is successful, then call the callback function if provided. Check if response code is 200 or 400 (is ok)

    if (callback === undefined) {
      callback = () => {};
    }

    // add registered token to message if we have one
    if (this.token) {
      message.token = this.token;
    }

    fetch('/dnd/backend/action', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(message),
    })
      .then(response => {
        if (!response.ok) {
          console.error('SSEService: Action failed: ', message);
        }
        return response.json();
      })
      .then(data => {
        console.log('SSEService: Received response:', data);
        callback(data);

        if (!suppressMessageHandlers) {
          this.messageHandlers
            .filter(handler => handler.messageType === data.type)
            .forEach(handler => handler.callback(data));
        }
      })
      .catch(error => {
        console.error('SSEService: Error sending message', error);
      });

  }



  disconnect() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}




export default SSEService;