import React from 'react';
import './RoundBoxPage.css';

const RoundedBoxPage = ({ items, callback }) => {
  console.log("items", items)
  return (
    <div className="rounded-box-page">
      {items.map((item, index) => (
        <div key={index} className={`rounded-box${index === 0 ? ' first-box' : ''}`}
        
        onClick={callback ? () => {callback(item.id)} : () => {alert("No callback set")}}
        
        >
          <div className="box-content">
            <div className="box-header">{item.name}</div>
            <div className="box-body">{index === 0 ? "no description :c" : item.gold + "GP"}</div>
          </div>
        </div>
      ))}
    </div>
  );
};

export { RoundedBoxPage };
