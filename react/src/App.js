import './App.css';
import React, { Component, useEffect, useState } from 'react';
import { WebSocketProvider, useWebSocket } from './components/WebSocketContext';
import Game from './components/Game';
import { MatchProvider } from './components/MatchContext';



function App() {
  return (
    // global div with a grey background background-color: #333;
    <div className="global-container">
      <WebSocketProvider>
        <MatchProvider>
          <Game/>
        </MatchProvider>
      </WebSocketProvider>
    </div>
  );
}

export default App;
