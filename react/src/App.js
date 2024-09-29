import './App.css';
import React, { Component, useEffect, useState } from 'react';
import { SSEProvider, useSSE } from './components/SSEContext';
import Game from './components/Game';
import { MatchProvider } from './components/MatchContext';



function App() {          // App component    
  return (
    // global div with a grey background background-color: #333;
    <div className="global-container">
      <SSEProvider>
        <MatchProvider>
          <Game/>
        </MatchProvider>
      </SSEProvider>
    </div>
  );
}

export default App;
