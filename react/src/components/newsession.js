import React, { Component } from "react";

class Newsession extends Component {

    constructor(props) {
        super(props);
        this.state = {
            gameName: "",
            gameDescription: "",
            gamePW: "",
            creationCode: ""
        }
    }

    render() {
        return (
            <div className="inner-container">
                <h2>New Session</h2>
                <div className="inner-new-container">
                    <div>
                        <input placeholder="DnD Campaign #47" type="text" title="Name of campaign" onChange={(e) => this.setState({gameName: e.target.value})} />
                        <input placeholder="Description" type="text" title="Description of your campaign. Can be left blank" onChange={(e) => this.setState({gameDescription: e.target.value})} />
                        <input placeholder="DM Password" type="text" title="You can set a passphrase which you will have to enter everytime you join again as DM in this created campaign. Can be left blank." onChange={(e) => this.setState({gamePW: e.target.value})} />
                        <input placeholder="Creation-Code" type="text" title="Creation-Code which is required to create a new campaign" onChange={(e) => this.setState({creationCode: e.target.value})} />
                    </div>
                    <button className="game-button-small" onClick={() => this.props.createSession(this.state)}>Submit</button>
                </div>
            </div>
        );
    }
}

export {Newsession};