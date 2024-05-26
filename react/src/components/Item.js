import React from 'react';
import './Item.css';

const rarityNames = {
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
    8: '',
  }
  

const Item = ({ id, name, count, description, value, image, rarity, type, onRightClick, isDraggable }) => {
    if (!image) {
      image = 'https://www.dndbeyond.com/attachments/2/741/potion.jpg';
    }

    const handleDragStart = (e) => {
        e.dataTransfer.setData('id', id);
    };
  
    return (
      <div className="item-container"
        onContextMenu={(e) => {
          e.preventDefault();
          onRightClick(e);
        }}
        draggable={isDraggable}
        onDragStart={isDraggable ? handleDragStart : undefined}
      >
        <img src={image} alt={name} className={`item-image ${rarity}`} />
        <div className="item-content">
          <div className={`item-name ${rarity}`}>{name}</div>
          {count > 1 && <div className={`item-name count`}>({count})</div>}
          <div className="item-description">{description}</div>
          <div className="item-type">{typeNames[type]}</div>
          <div className="item-value">{`${value}GP`}</div>
        </div>
      </div>
    );
  };

export default Item;