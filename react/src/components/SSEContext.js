import React, { createContext, useContext } from 'react';
import SSEService from './SSEService';

const SSEContext = createContext(null);

export const SSEProvider = ({ children }) => {
  const sseService = new SSEService();

  return (
    <SSEContext.Provider value={sseService}>
      {children}
    </SSEContext.Provider>
  );
};

export const useSSE = () => {
  return useContext(SSEContext);
};
