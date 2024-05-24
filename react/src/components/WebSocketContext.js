import React, { createContext, useContext } from 'react';
import WebSocketService from './WebSocketService';

const WebSocketContext = createContext(null);

export const WebSocketProvider = ({ children }) => {
  const webSocketService = new WebSocketService();

  return (
    <WebSocketContext.Provider value={webSocketService}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = () => {
  return useContext(WebSocketContext);
};