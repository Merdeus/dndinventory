import React, { Component, useEffect, useState } from "react";

import {Joinsession} from "./joinsession.js";
import {Newsession} from "./newsession.js";
import {useWebSocket} from "./WebSocketContext.js";
import './SelectGame.css';

const SelectGame = () => {
  const [game, setGame] = useState(null);

  const webSocketService = useWebSocket();

  const createSession = (tab) => {
    const { gameName, gameDescription, gamePW, creationCode } = tab;
    console.log("Creating session for game: ", gameName);
    const protocolUse = process.env.REACT_APP_USE_WS_ENV && process.env.REACT_APP_USE_WS_ENV == 1 ? "ws" : "wss";
    console.log("Using protocol: " + protocolUse, process.env.REACT_APP_USE_WS_ENV)
    const domain = window.location.hostname;
    webSocketService.connect(protocolUse + '://' + domain + ':8273', () => {
      webSocketService.sendMessage({
        type: "register", 
        action: "createSession",
        create: {
          name: gameName,
          description: gameDescription,
          dm_pass: gamePW,
          creationCode: creationCode
        }
      });
    });
  };

  const joinSession = (joinCode) => {
    console.log("Joining session with ID: " + joinCode);

    const protocolUse = process.env.REACT_APP_USE_WS_ENV && process.env.REACT_APP_USE_WS_ENV == 1 ? "ws" : "wss";
    console.log("Using protocol: " + protocolUse, process.env.REACT_APP_USE_WS_ENV)
    const domain = window.location.hostname;
    webSocketService.connect(protocolUse + '://' + domain + ':8273', () => {
      webSocketService.sendMessage({
        type: "register", 
        action: "joinSession",
        join: {
          code: joinCode
        }
      });
    });

  };

  return (
    <div className="select-game-container">
      <h1>Inventory Management</h1>
      <div className="button-container">
        <button className="game-button" onClick={() => setGame("joinsession")}>
          Join Session
        </button>
        <button className="game-button" onClick={() => setGame("createnewsession")}>
          Create New Session
        </button>
      </div>
      {game === "joinsession" && (
        <div className="fade-in">
          <Joinsession joinSession={joinSession} />
        </div>
      )}
      {game === "createnewsession" && (
        <div className="fade-in">
          <Newsession createSession={createSession} />
        </div>
      )}
    </div>
  );
};

export { SelectGame };