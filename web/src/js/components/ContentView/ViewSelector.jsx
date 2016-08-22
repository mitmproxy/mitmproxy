import React, { PropTypes, Component } from 'react'
import classnames from 'classnames'
import { connect } from 'react-redux'
import * as ContentViews from './ContentViews'
import { setContentView } from "../../ducks/ui/flow";

function ViewItem({ name, setContentView, children }) {
    return (
        <li>
            <a href="#" onClick={() => setContentView(name)}>
                {children}
            </a>
        </li>
    )
}


/*ViewSelector.propTypes = {
    contentViews: PropTypes.array.isRequired,
    activeView: PropTypes.string.isRequired,
    isEdit: PropTypes.bool.isRequired,
    isContentViewSelectorOpen: PropTypes.bool.isRequired,
    setContentViewSelectorOpen: PropTypes.func.isRequired
}*/


class ViewSelector extends Component {
      constructor(props, context) {
        super(props, context)
        this.close = this.close.bind(this)
        this.state = {open: false}
    }
    close() {
        this.setState({open: false})
        document.removeEventListener('click', this.close)
    }

    onDropdown(e){
        e.preventDefault()
        this.setState({open: !this.state.open})
        document.addEventListener('click', this.close)
    }

    render() {
        const {contentViews, activeView, isEdit, setContentView} = this.props
        let edit = ContentViews.Edit.displayName

        return (
            <div className={classnames('dropup pull-left', { open: this.state.open })}>
                <a className="btn btn-default btn-xs"
                   onClick={ e => this.onDropdown(e) }
                   href="#">
                    <b>View:</b> {activeView}<span className="caret"></span>
                </a>
                <ul className="dropdown-menu" role="menu">
                    {contentViews.map(name =>
                        <ViewItem key={name} setContentView={setContentView} name={name}>
                            {name.toLowerCase().replace('_', ' ')}
                        </ViewItem>
                    )}
                    {isEdit &&
                    <ViewItem key={edit} setContentView={setContentView} name={edit}>
                        {edit.toLowerCase()}
                    </ViewItem>
                    }
                </ul>
            </div>
        )
    }
}

export default connect (
    state => ({
        contentViews: state.settings.contentViews,
        activeView: state.ui.flow.contentView,
        isEdit: !!state.ui.flow.modifiedFlow,
    }), {
        setContentView,
    }
)(ViewSelector)
