import React from 'react';
import './ItemDetailModal.css';

const rarityNames = {
  0: 'Mundane',
  1: 'Common',
  2: 'Uncommon',
  3: 'Rare',
  4: 'Very Rare',
  5: 'Epic',
  6: 'Legendary',
  7: 'Quest Item',
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

const ItemDetailModal = ({ isOpen, item, onClose }) => {
  if (!isOpen || !item) return null;

  const { name, description, value, img, rarity, type, count = 1 } = item;

  return (
    <div className="modal-overlay">

    <div className="item-detail-modal-overlay" onClick={onClose}>
      <div className="item-detail-modal" onClick={(e) => e.stopPropagation()}>
        <div className="item-detail-modal-header">
            <h3 className="item-detail-modal-title">Item Details</h3>
          <button className="item-detail-modal-close" onClick={onClose}>
            &times;
          </button>
        </div>
        <div className="item-detail-modal-content">

            <div className="item-detail-modal-img-titel">
                <img src={img} alt={name} className="item-detail-modal-image" />
                <h2 className="item-detail-modal-name">{name}</h2>
            </div>

            <p className={`item-detail-modal-rarity ${rarityNames[rarity]}`}>
            Rarity: {rarityNames[rarity]}
            </p>
            <p className="item-detail-modal-type">Type: {typeNames[type]}</p>
            <p className="item-detail-modal-type">Description:</p>
            <p className="item-detail-modal-description">{description}</p>
            <p className="item-detail-modal-value">Value: {value * count} GP</p>
            {count > 1 && <p className="item-detail-modal-count">Count: {count}</p>}
        </div>
      </div>
    </div>
    </div>

  );
};

export default ItemDetailModal;
