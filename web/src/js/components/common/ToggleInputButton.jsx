import React, { Component, PropTypes } from 'react'
import classnames from 'classnames'
import { Key } from '../../utils'

export default class ToggleInputButton extends Component {

    static propTypes = {
        name: PropTypes.string.isRequired,
        txt: PropTypes.string.isRequired,
        onToggleChanged: PropTypes.func.isRequired
    }

    constructor(props) {
        super(props)
        this.state = { txt: props.txt }
    }

    onChange(e) {
        this.setState({ txt: e.target.value })
    }

    onKeyDown(e) {
        e.stopPropagation()
        if (e.keyCode === Key.ENTER) {
            this.props.onToggleChanged(this.state.txt)
        }
    }

    render() {
        return (
            <div className="input-group toggle-input-btn">
                <span className="input-group-btn"
                      onClick={() => this.props.onToggleChanged(this.state.txt)}>
                    <div className={classnames('btn', this.props.checked ? 'btn-primary' : 'btn-default')}>
                        <span className={classnames('fa', this.props.checked ? 'fa-check-square-o' : 'fa-square-o')}/>
                        &nbsp;
                        {this.props.name}
                    </div>
                </span>
                <input
                    className="form-control"
                    placeholder={this.props.placeholder}
                    disabled={this.props.checked}
                    value={this.state.txt}
                    type={this.props.inputType}
                    onChange={e => this.onChange(e)}
                    onKeyDown={e => this.onKeyDown(e)}
                />
            </div>
        )
    }
}
