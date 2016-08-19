import React, { Component, PropTypes } from 'react'
import classnames from 'classnames'

export const Divider = () => <hr className="divider"/>

export default class Dropdown extends Component {

    static propTypes = {
        dropup: PropTypes.bool,
        className: PropTypes.string,
        btnClass: PropTypes.string.isRequired
    }

    static defaultProps = {
        dropup: false
    }

    constructor(props, context) {
        super(props, context)
        this.state = { open: false }
        this.close = this.close.bind(this)
        this.open = this.open.bind(this)
    }

    close() {
        this.setState({ open: false })
        document.removeEventListener('click', this.close)
    }

    open(e){
        e.preventDefault()
        if (this.state.open) {
            return
        }
        this.setState({open: !this.state.open})
        document.addEventListener('click', this.close)
    }

    render() {
        const {dropup, className, btnClass, text, children} = this.props
        return (
            <div className={classnames( (dropup ? 'dropup' : 'dropdown'), className, { open: this.state.open })}>
                <a href='#' className={btnClass}
                   onClick={this.open}>
                    {text}
                </a>
                <ul className="dropdown-menu" role="menu">
                    {children.map ( (item, i) =>  <li key={i}> {item} </li> )}
                </ul>
            </div>
        )
    }
}
