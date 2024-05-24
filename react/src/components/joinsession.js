import React, { Component } from "react";

class Joinsession extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            sessionID: null
        }
    }

    render() {
        return (
            <div className="inner-container">
                <h2>Join Session</h2>
                <div className="inner-new-container">
                    <input type="text" placeholder="ABCDEF" onChange={(e) => this.setState({sessionID: e.target.value})} />
                    <button className="game-button-small" onClick={() => this.props.joinSession(this.state.sessionID)}>Submit</button>
                </div>
            </div>
        );
    }
}


export {Joinsession};