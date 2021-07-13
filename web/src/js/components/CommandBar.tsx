import React, { useState, useEffect, Component } from 'react'
import classnames from 'classnames'
import { Key, fetchApi } from '../utils'
import Filt from '../filt/command'

export function AvailableCommands({input, commands}) {
    if (!commands) return null
    let availableCommands = []
    for (const [command, args] of Object.entries(commands)) {
        if (command.startsWith(input)) {
            availableCommands.push(command)
        }
    }
    return <div className="available-commands popover bottom">Available Commands: {JSON.stringify(availableCommands)}</div>
}

export function ArgumentSuggestion({nextArgs, currentArg}){
    let results = []
    for (let i = 0; i < nextArgs.length; i++) {
        if (i==currentArg) {
            results.push(<mark>{nextArgs[i]}</mark>)
            continue
        }
        results.push(<span>{nextArgs[i]} </span>)
    }
    return (<div className="argument-suggestion popover top">
        <div className="arrow"/>
        <div className="popover-content">
            Argument suggestion: {results}
        </div>
    </div>)
}

export default function CommandBar() {
    const [input, setInput] = useState("")
    const [command, setCommand] = useState("")
    const [results, setResults] = useState([])
    const [history, setHistory] = useState([])
    const [currentPos, setCurrentPos] = useState(0)
    const [allCommands, setAllCommands] = useState({})
    const [nextArgs, setNextArgs] = useState([])
    const [currentArg, setCurrentArg] = useState(0)
    const [commandHelp, setCommandHelp] = useState("")

    useEffect(() => {
        fetchApi('/commands', { method: 'GET' })
        .then(response => response.json())
        .then(data => setAllCommands(data))
    }, [])

    const parseCommand = (input) => {
        const parts = Filt.parse(input)
        if (allCommands["commands"].hasOwnProperty(parts[0])){
            setCommand(parts[0])
        } else {
            setCommand("")
        }

        const nextArgs = allCommands["commands"][parts[0]]?.map(arg => arg.name)

        if (nextArgs) {
            setNextArgs([parts[0], ...nextArgs])
            setCurrentArg(parts.length-1)
        }
    }

    const onChange = (e) =>  {
        setInput(e.target.value)
    }

    const onKeyDown = (e) => {
        if (e.keyCode === Key.ENTER) {
            const body = {"command": input}
            const newHistory = Object.assign([], history)
            newHistory.splice(currentPos, 0, input)

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
                setNextArgs([])

                setResults([...results, {"id": results.length, "result": data.result}])
            })

            setInput("")
        }
        if (e.keyCode === Key.UP) {
            if (currentPos > 0) {
                setInput(history[currentPos - 1])
                setCurrentPos(currentPos - 1)
            }
        }
        if (e.keyCode === Key.DOWN) {
            setInput(history[currentPos])
            if (currentPos < history.length -1) {
                setCurrentPos(currentPos + 1)
            }
        }
        e.stopPropagation()
    }

    const onKeyUp = (e) => {
        if (input == "") return
        parseCommand(input)
        e.stopPropagation()
    }

    return (
        <div className="command">
            <div className="command-title">
                Command Result
            </div>
            <div className="command-result">
                {results.map(result => (
                    <div key={result.id}>
                        {result.result}
                    </div>
                ))}
            </div>
            { nextArgs.length > 0 && <ArgumentSuggestion nextArgs={nextArgs} currentArg={currentArg} /> }
            <div className={classnames('command-input input-group')}>
                <span className="input-group-addon">
                    <i className={'fa fa-fw fa-terminal'}/>
                </span>
                <input
                    type="text"
                    placeholder="Enter command"
                    className="form-control"
                    value={input}
                    onChange={onChange}
                    onKeyDown={onKeyDown}
                    onKeyUp={onKeyUp}
                />
            </div>
            { !command && <AvailableCommands input={input} commands={allCommands["commands"]} /> }
        </div>
    )
}