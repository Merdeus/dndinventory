// screen for player selection
import React, { Component } from 'react';
import './SelectPlayer.css';
import { RoundedBoxPage } from './RoundBoxPage';

const SelectPlayer = ({items, callback}) => {

    // add Dungeon Master to the list in the beginning of the list of players, but only if it does not already exist
    if (items[0] === undefined || items[0].id !== -1)
        items.unshift({ id: -1, name: 'Dungeon Master', description: 'The one who creates the world and controls the game', gold: 0 });

    return (
        <div className="select-player-container">
            <div className="select-player-content">
                <h2 className="select-player-title">Player selection</h2>
                <RoundedBoxPage items={items} callback = {callback} />
            </div>
        </div>
        
    );

}


export { SelectPlayer };