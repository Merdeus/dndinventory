import React, { useState, useEffect } from 'react';
import { useMatch } from './MatchContext';
import './Item.css';

const rarityNames = {
  0: 'mundane',
  1: 'common',
  2: 'uncommon',
  3: 'rare',
  4: 'veryrare',
  5: 'epic',
  6: 'legendary',
  7: 'questitem',
};

const typeNames = {
  1: 'Weapon',
  2: 'Armor',
  3: 'Adventure Gear',
  4: 'Tool',
  5: 'Consumable',
  6: 'Magical Item',
  7: 'Valuable',
  8: 'Scroll',
  9: 'Shield',
  10: 'Ring',
  11: 'Staff',
  12: 'Miscellaneous',
  13: 'Wondrous Item',
}

function splitAtFirstNewline(str) {
  const newlineIndex = str.indexOf('\n');
  
  if (newlineIndex === -1) {
      return str;
  }
  
  const beforeNewline = str.substring(0, newlineIndex);
  return beforeNewline;
}
  

const Item = ({ id, name, count, description, value, image, rarity, type, onRightClick, isDraggable, smaller, onClick, lootItemID, isLootListItem, lootClaim, lootVote }) => {

  const { matchState, updateMatchState } = useMatch();
  const [showClaimButton, setShowClaimButton] = useState(false);
  const [showVoteButton, setShowVoteButton] = useState(false);

  useEffect(() => {

    if (isLootListItem) {
      if (matchState.loot.phase == 1) {
        setShowClaimButton(true);
        setShowVoteButton(false);
      } else if (matchState.loot.phase == 2) {
        setShowClaimButton(false);
        setShowVoteButton(true);
      } else {
        setShowClaimButton(false);
        setShowVoteButton(false);
      }
    }

  }, [matchState]);



  if (!image) {
    image = 'https://www.dndbeyond.com/attachments/2/741/potion.jpg';
  }

  if (!count)
  {
      count = 1;
  }

  const handleDragStart = (e) => {
      e.dataTransfer.setData('id', id);
  };

  const getClaimedByString = () => {
    const claimsDict = matchState.loot.items[lootItemID].ext.claims;
    const playersDict = matchState.game.players;
    const claimedKeys = Object.keys(claimsDict).filter(key => claimsDict[key]);
    const claimedNames = claimedKeys.map(key => playersDict[key].name);
    return `Claimed by ${claimedNames.join(", ")}`;
  };

  return (
    <div className={`item-container ${smaller ? 'smaller' : ''} ${rarity}`}
      onContextMenu={(e) => {
        e.preventDefault();
        onRightClick(e);
      }}
      draggable={isDraggable}
      onDragStart={isDraggable ? handleDragStart : undefined}
      onClick={onClick}
    >
      <img src={image} alt={name} className={`item-image ${rarity}`} />
      <div className="item-content">
        <div className={`item-name ${rarity}`}>{name}</div>
        {count > 1 && <div className={`item-name count`}>({count})</div>}
        {showClaimButton ? (
          matchState.loot.waiting[matchState.player] && !matchState.loot.items[lootItemID].ext.claims[matchState.player] ? (
          <button className="loot-vote-button" onClick={(e) => { e.stopPropagation(); lootClaim(id); }}>Claim this item for yourself</button>
          ) : (
            <div className="item-loot-text">
              {Object.values(matchState.loot.items[lootItemID].ext.claims).length > 0 ? getClaimedByString() : "Nobody claimed this item"}
            </div>
          )
        ) : showVoteButton ? (
          <button className="loot-vote-button" onClick={(e) => { e.stopPropagation(); lootVote(id); }}>Vote for this item</button>
        ) : (
          <>
            <div className="item-description">{splitAtFirstNewline(description)}</div>
            <div className="item-type">{typeNames[type]}</div>
            <div className="item-value">{`${value * count}GP`}</div>
          </>
        )}
      </div>
    </div>
  );
};

export default Item;