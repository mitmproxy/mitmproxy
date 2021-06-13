import React, {Component} from 'react'
import PropTypes from 'prop-types'
import { Manager, Reference, Popper } from 'react-popper';
import classnames from 'classnames'

export const Divider = () => <hr className="divider"/>

export default class DropdownSubMenu extends Component {

    static propTypes = {
        dropup: PropTypes.bool,
        className: PropTypes.string,
    }

    static defaultProps = {
        dropup: false
    }

    constructor(props, context) {
        super(props, context)
        this.state = {open: false}
        this.close = this.close.bind(this)
        this.open = this.open.bind(this)
    }

    close() {
        this.setState({open: false})
        document.removeEventListener('click', this.close)
    }

    open(e) {
        e.preventDefault()
        if (this.state.open) {
            return
        }
        e.stopPropagation();
        this.setState({open: !this.state.open})
        document.addEventListener('click', this.close)
    }

    render() {
        const {text, children} = this.props

        return (
            <li className="dropdown-submenu">
                <Manager>
                    <Reference>
                        {({ ref }) => (
                            <a tabIndex="-1" ref={ref} href="#">{text}</a>
                        )}
                    </Reference>
                    <Popper
                        placement="bottom-end"
                        modifiers={[
                            {
                                name: 'offset',
                                options: {
                                    offset: [0, 30],
                                }
                            },
                        ]}
                    >
                        {({ ref, style, placement, arrowProps }) => (
                            <ul ref={ref} style={style} data-placement={placement} className="dropdown-menu pull-left">
                                {children.map((item, i) => <li key={i}> {item} </li>)}
                            </ul>
                        )}
                    </Popper>
                </Manager>
            </li>
        )
    }
}
