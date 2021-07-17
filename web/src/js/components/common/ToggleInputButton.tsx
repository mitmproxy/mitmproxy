import React, { Component } from 'react'
import classnames from 'classnames'
import { Key } from '../../utils'

type ToggleInputButtonProps = {
    name: string,
    txt: string,
    onToggleChanged: (string) => void,
    checked: boolean,
    placeholder: string,
    inputType: string,
}

type ToggleInputButtonStates = {
    txt: string,
}

export default class ToggleInputButton extends Component<ToggleInputButtonProps, ToggleInputButtonStates> {
    constructor(props) {
        super(props)
        this.state = { txt: props.txt || '' }
    }

    onKeyDown(e) {
        e.stopPropagation()
        if (e.keyCode === Key.ENTER) {
            this.props.onToggleChanged(this.state.txt)
        }
    }

    render() {
        const {checked, onToggleChanged, name, inputType, placeholder} = this.props
        return (
            <div className="input-group toggle-input-btn">
                <span className="input-group-btn"
                      onClick={() => onToggleChanged(this.state.txt)}>
                    <div className={classnames('btn', checked ? 'btn-primary' : 'btn-default')}>
                        <span className={classnames('fa', checked ? 'fa-check-square-o' : 'fa-square-o')}/>
                        &nbsp;
                        {name}
                    </div>
                </span>
                <input
                    className="form-control"
                    placeholder={placeholder}
                    disabled={checked}
                    value={this.state.txt}
                    type={inputType || 'text'}
                    onChange={e => this.setState({ txt: e.target.value })}
                    onKeyDown={e => this.onKeyDown(e)}
                />
            </div>
        )
    }
}
