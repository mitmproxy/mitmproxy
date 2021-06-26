import React, { useState, useEffect, Component } from 'react'
import classnames from 'classnames'
import { Key, fetchApi } from '../utils'
import Filt from '../filt/command'

export default function CommandBar() {
    const [command, setCommand] = useState("")
    const [results, setResults] = useState([])
    const [history, setHistory] = useState([])
    const [currentPos, setCurrentPos] = useState(0)
    const [args, setArgs] = useState({})
    const [nextArgs, setNextArgs] = useState([])

    useEffect(() => {
        fetchApi('/arguments')
        .then(response => response.json())
        .then(data => setArgs(data))
    }, [])

    const parseCommand = (input) => {
        const parts = Filt.parse(input)

        const nextArgs = args[parts[0]]

        if (nextArgs) {
            setNextArgs([parts[0], ...nextArgs])
        }
    }

    const onChange = (e) =>  {
        setCommand(e.target.value)
    }

    const onKeyDown = (e) => {
        if (e.keyCode === Key.ENTER) {
            const body = {"command": command}
            const newHistory = Object.assign([], history)
            newHistory.splice(currentPos, 0, command)

            fetchApi(`/commands`, {
                method: 'POST',
                body: JSON.stringify(body),
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                setHistory(newHistory)
                setCurrentPos(currentPos + 1)

                if (data.result == "") return
                setResults([...results, {"id": results.length, "result": data.result}])
            })

            setCommand("")
        }
        if (e.keyCode === Key.UP) {
            if (currentPos > 0) {
                setCommand(history[currentPos - 1])
                setCurrentPos(currentPos - 1)
            }
        }
        if (e.keyCode === Key.DOWN) {
            setCommand(history[currentPos])
            if (currentPos < history.length -1) {
                setCurrentPos(currentPos + 1)
            }
        }
        e.stopPropagation()
    }

    const onKeyUp = (e) => {
        if (command == "") return
        parseCommand(command)
        e.stopPropagation()
    }

    return (
        <>
            <div className="command">
                Command Result
            </div>
            <div className="command-result">
                {results.map(result => (
                    <div key={result.id}>
                        {result.result}
                    </div>
                ))}
            </div>
            { nextArgs ? <div className="command-suggestion">Argument suggestion: {nextArgs.join(" ")}</div> : null }
            <div className={classnames('command-input input-group')}>
                <span className="input-group-addon">
                    <i className={'fa fa-fw fa-terminal'}/>
                </span>
                <input
                    type="text"
                    placeholder="Enter command"
                    className="form-control"
                    value={command}
                    onChange={onChange}
                    onKeyDown={onKeyDown}
                    onKeyUp={onKeyUp}
                />
            </div>
        </>
    )
}