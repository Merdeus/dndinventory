import React, {useState} from 'react';
import './GoldModal.css';

const GoldModal = ({ prevGold, onClose, onSubmit }) => {
	const [goldChange, setGoldChange] = useState(prevGold || 0);
  
	const handleGoldChange = (amount) => {
	  setGoldChange(Math.max(goldChange + amount, 0));
	};
  
	const handleInputChange = (event) => {
	  setGoldChange(parseInt(event.target.value) || 0);
	};
  
	const handleCancel = () => {
	  setGoldChange(0);
	  onClose();
	};
  
	const handleSubmit = () => {
	  onSubmit(goldChange);
	  setGoldChange(0);
	  onClose();
	};
  
	return (
		<div className="modal-overlay"><div className="modal">
	  <div className="gold-modal">
		<div className="button-row">
		  <div className="gold-button" onClick={() => handleGoldChange(1)}>+1</div>
		  <div className="gold-button" onClick={() => handleGoldChange(10)}>+10</div>
		  <div className="gold-button" onClick={() => handleGoldChange(100)}>+100</div>
		  <div className="gold-button" onClick={() => handleGoldChange(1000)}>+1000</div>
		</div>
		<div className="button-row">
		  <div className="gold-button" onClick={() => handleGoldChange(-1)}>-1</div>
		  <div className="gold-button" onClick={() => handleGoldChange(-10)}>-10</div>
		  <div className="gold-button" onClick={() => handleGoldChange(-100)}>-100</div>
		  <div className="gold-button" onClick={() => handleGoldChange(-1000)}>-1000</div>
		</div>
		<input type="number" value={goldChange} onChange={handleInputChange} className="gold-input" />
		<div className="button-row-last">
		  <div className="gold-button cancel-button" onClick={handleCancel}>Cancel</div>
		  <div className="gold-button submit-button" onClick={handleSubmit}>Submit</div>
		</div>
	  </div></div></div>
	);
};

export default GoldModal;