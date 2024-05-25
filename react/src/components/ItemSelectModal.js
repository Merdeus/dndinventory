import React, { useState } from 'react';
import './ItemSelectModal.css';

const ItemSelectModal = ({ isOpen, onClose, onSave }) => {

  const defaultImages = [
    'https://www.dndbeyond.com/attachments/2/741/potion.jpg',
    'https://www.dndbeyond.com/attachments/2/742/weapon.jpg',
    'https://www.dndbeyond.com/attachments/2/740/armor.jpg'
  ];


  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [imageUrl, setImageUrl] = useState(defaultImages[0]);
  const [customImageUrl, setCustomImageUrl] = useState('');
  const [rarity, setRarity] = useState('1');
  const [itemType, setItemType] = useState('1');
  const [value, setValue] = useState(0);
  const [isCustomImage, setIsCustomImage] = useState(false);

  const handleImageSelect = (index) => {
    if (index === 3) {
      setIsCustomImage(true);
      setImageUrl('');
    } else {
      setIsCustomImage(false);
      setImageUrl(defaultImages[index]);
    }
  };

  const handleSave = () => {

    if (!name || !description || (!imageUrl && !isCustomImage)) {
      alert('Please fill out all fields');
      return;
    }

    const newItem = {
      name,
      description,
      image: isCustomImage ? customImageUrl : imageUrl,
      rarity,
      itemType,
      value
    };
    onSave(newItem);
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal">
        <h2>Create New Item</h2>
        <label className="ItemModalLabel">
          Name:  
          <input type="text" value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label className="ItemModalLabel">
          Description:
          <textarea className="ItemModalTextArea" value={description} onChange={(e) => setDescription(e.target.value)} />
        </label>
        <div>
          <label>Image:</label>
          <div className="image-selection">
            {defaultImages.map((img, index) => (
              <img
                key={index}
                src={img}
                alt={`Default ${index + 1}`}
                className={`image-option ${imageUrl === img ? 'selected' : ''}`}
                onClick={() => handleImageSelect(index)}
              />
            ))}
            <div
              className={`image-option ${isCustomImage ? 'selected' : ''}`}
              onClick={() => handleImageSelect(3)}
            >
              <label className="ItemModalLabel">Custom</label>
            </div>
          </div>
          {isCustomImage && (
            <input
              type="text"
              placeholder="Enter custom image URL"
              value={customImageUrl}
              onChange={(e) => setCustomImageUrl(e.target.value)}
            />
          )}
        </div>
        <label>
          Rarity:
          <select value={rarity} onChange={(e) => setRarity(e.target.value)}>
            <option value="1">Common</option>
            <option value="2">Uncommon</option>
            <option value="3">Rare</option>
            <option value="4">Very Rare</option>
            <option value="5">Epic</option>
            <option value="6">Legendary</option>
            <option value="7">Quest Item</option>
          </select>
        </label>
        <label>
          Item Type:
          <select value={itemType} onChange={(e) => setItemType(e.target.value)}>
            <option value="1">Weapon</option>
            <option value="2">Armor</option>
            <option value="4">Tool</option>
            <option value="5">Consumable</option>
            <option value="6">Magical Item</option>
            <option value="3">Adventure Gear</option>
            <option value="7">Valuable</option>
          </select>
        </label>
        <label>
          Value:
          <input
            type="number"
            value={value}
            onChange={(e) => setValue(parseInt(e.target.value))}
          />
        </label>
        <div className="modal-buttons">
          <button onClick={onClose}>Cancel</button>
          <button onClick={handleSave}>Save</button>
        </div>
      </div>
    </div>
  );
};

export default ItemSelectModal;
