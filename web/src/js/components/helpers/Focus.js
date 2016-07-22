import ReactDOM from 'react-dom'

export default function FocusHelper(shouldFocus) {
    if (!shouldFocus) {
        return () => {
        }
    }
    return ref => {
        if (ref) {
            ReactDOM.findDOMNode(ref).focus()
        }
    }
}
