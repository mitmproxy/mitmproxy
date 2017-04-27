import React  from 'react'
import PropTypes from 'prop-types'
import ReactDOM from 'react-dom'
import _ from 'lodash'

import {Key} from '../utils.js'

Prompt.propTypes = {
    options: PropTypes.array.isRequired,
    done: PropTypes.func.isRequired,
    prompt: PropTypes.string,
}

export default function Prompt({ prompt, done, options }) {
    const opts = []

    for (let i = 0; i < options.length; i++) {
        let opt = options[i]
        if (_.isString(opt)) {
            let str = opt
            while (str.length > 0 && keyTaken(str[0])) {
                str = str.substr(1)
            }
            opt = { text: opt, key: str[0] }
        }
        if (!opt.text || !opt.key || keyTaken(opt.key)) {
            throw 'invalid options'
        }
        opts.push(opt)
    }

    function keyTaken(k) {
        return _.map(opts, 'key').includes(k)
    }

    function onKeyDown(event) {
        event.stopPropagation()
        event.preventDefault()
        const key = opts.find(opt => Key[opt.key.toUpperCase()] === event.keyCode)
        if (!key && event.keyCode !== Key.ESC && event.keyCode !== Key.ENTER) {
            return
        }
        done(key.key || false)
    }

    return (
        <div tabIndex="0" onKeyDown={onKeyDown} className="prompt-dialog">
            <div className="prompt-content">
            {prompt || <strong>Select: </strong> }
            {opts.map(opt => {
                const idx = opt.text.indexOf(opt.key)
                function onClick(event) {
                    done(opt.key)
                    event.stopPropagation()
                }
                return (
                    <span key={opt.key} className="option" onClick={onClick}>
                        {idx !== -1 ? opt.text.substring(0, idx) : opt.text + '('}
                        <strong className="text-primary">{opt.key}</strong>
                        {idx !== -1 ? opt.text.substring(idx + 1) : ')'}
                    </span>
                )
            })}
            </div>
        </div>
    )
}
