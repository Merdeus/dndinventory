import logo from './logo.svg';
import './App.css';
import React, { Component, useEffect, useState } from 'react';
import { WebSocketProvider, useWebSocket } from './components/WebSocketContext';
import Game from './components/Game';
import { MatchProvider } from './components/MatchContext';



function App() {



  const players = [
    { name: 'Player 1' },
    { name: 'Player 2' },
    { name: 'Player 3' },
  ];


  const items = [
    { id: 1, name: 'Sword', description: 'A sharp blade', value: 150 },
    { id: 2, name: 'Shield', description: 'Protects you from attacks', value: 100 },
    { id: 3, name: 'Potion', description: 'Heals your wounds', value: 50 },
    { id: 4, name: 'Helmet', description: 'Protects your head', value: 75 },
    { id: 5, name: 'Shard', description: 'Reeeee', value: 75 },
    { id: 6, name: 'Excalibur', description: 'Very long text. Like verrrrrrry long. You know? Just to figure out if the given text bounds are fitting with the div container. Very important. Very much. Ogg. Ogg. Ogg. Oggg. Ogg. Very important. Very important.', value: 50 },
    { id: 7, name: 'Helmet', description: 'Protects your head', value: 75 },
    { id: 8, name: 'Shard', description: 'Reeeee', value: 175 },
    { id: 9, name: 'vHelmet', description: 'Protects your head', value: 75 },
    { id: 10, name: 'Shard', description: 'Reeeee', value: 75 },
    { id: 11, name: 'Helmet', description: 'Protects your head', value: 75 },
    { id: 12, name: 'Ultra Shard', description: 'Reeeee', value: 5 },
    { id: 13, name: 'Helmet', description: 'Protects your head', value: 75 },
    { id: 14, name: 'Shard', description: 'Reeeee', value: 75 },


  ];


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
