// MatchContext.js
import React, { createContext, useContext, useState, useEffect } from 'react';

// Create a Context
const MatchContext = createContext();

// Create a provider component
export const MatchProvider = ({ children }) => {
  const [matchState, setMatchState] = useState({
    isDM : false,
    player: null,
    game: null,
    inventory: null,
    inventories: null,
    itemlist: []
  });

  const updateMatchState = (newVals) => {
    console.log("Updating match state", newVals)
    setMatchState(prevState => ({
      ...prevState,
      ...newVals
    }));
  };

  // update only the inventory. The inventory is a dictionary of items
  const updateInventory = (newInventory) => {
    setMatchState(prevState => ({
      ...prevState,
      inventory: newInventory
    }));
  };

  const updateInventories = (newInventories) => {
    setMatchState(prevState => ({
      ...prevState,
      inventories: {
        ...prevState.inventories,
        ...newInventories
      }
    }));
  };

  useEffect(() => {
    console.log("Matchstate updated:", matchState)
  }, [matchState]);

  return (
    <MatchContext.Provider value={{ matchState, updateMatchState, updateInventory, updateInventories }}>
      {children}
    </MatchContext.Provider>
  );
};

// Create a custom hook for easy access to the context
export const useMatch = () => useContext(MatchContext);
