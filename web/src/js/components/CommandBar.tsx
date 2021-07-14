import React, { useState, useEffect, Component } from 'react'
import classnames from 'classnames'
import { Key, fetchApi } from '../utils'
import Filt from '../filt/command'

function getAvailableCommands(commands, input = "") {
    if (!commands) return null
    let availableCommands = []
    for (const [command, args] of Object.entries(commands)) {
        if (command.startsWith(input)) {
            availableCommands.push(command)
        }
    }
    return availableCommands
}

export function CommandHelp({nextArgs, currentArg, help, description}){
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
            <div><strong>Argument suggestion:</strong> {results}</div>
            { help.includes("->") && <div><strong>Signature help: </strong>{help}</div>}
            { description && <div># {description}</div>}
        </div>
    </div>)
}

export default function CommandBar() {
    const [input, setInput] = useState("")
    const [originalInput, setOriginalInput] = useState("")
    const [currentCompletion, setCurrentCompletion] = useState(0)

    const [availableCommands, setAvailableCommands] = useState([])
    const [allCommands, setAllCommands] = useState({})
    const [nextArgs, setNextArgs] = useState([])
    const [currentArg, setCurrentArg] = useState(0)
    const [signatureHelp, setSignatureHelp] = useState("")
    const [description, setDescription] = useState("")

    const [results, setResults] = useState([])
    const [history, setHistory] = useState([])
    const [currentPos, setCurrentPos] = useState(0)

    useEffect(() => {
        fetchApi('/commands', { method: 'GET' })
        .then(response => response.json())
        .then(data => {
            setAllCommands(data)
            setAvailableCommands(getAvailableCommands(data["commands"]))
        })
    }, [])

    const parseCommand = (originalInput, input) => {
        const parts = Filt.parse(input)
        const originalParts = Filt.parse(originalInput)
        const commands = allCommands["commands"]

        setSignatureHelp(commands[parts[0]]?.signature_help)
        setDescription(commands[parts[0]]?.description)

        setAvailableCommands(getAvailableCommands(commands, originalParts[0]))

        const nextArgs = allCommands["commands"][parts[0]]?.args

        if (nextArgs) {
            setNextArgs([parts[0], ...nextArgs])
            setCurrentArg(parts.length-1)
        }
    }

    const onChange = (e) =>  {
        setInput(e.target.value)
        setOriginalInput(e.target.value)
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
            setOriginalInput("")
        }
        if (e.keyCode === Key.UP) {
            if (currentPos > 0) {
                setInput(history[currentPos - 1])
                setOriginalInput(history[currentPos -1])
                setCurrentPos(currentPos - 1)
            }
        }
        if (e.keyCode === Key.DOWN) {
            setInput(history[currentPos])
            setOriginalInput(history[currentPos])
            if (currentPos < history.length -1) {
                setCurrentPos(currentPos + 1)
            }
        }
        if (e.keyCode === Key.TAB) {
            setInput(availableCommands[currentCompletion])
            setCurrentCompletion((currentCompletion + 1) % availableCommands.length)
            e.preventDefault()
        }
        e.stopPropagation()
    }

    const onKeyUp = (e) => {
        if (input == "") return
        console.log("keyup event")
        parseCommand(originalInput, input)
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
            { signatureHelp && <CommandHelp nextArgs={nextArgs} currentArg={currentArg} help={signatureHelp} description={description}/> }
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
            <div className="available-commands popover bottom">Available Commands: {JSON.stringify(availableCommands)}</div>
        </div>
    )
}