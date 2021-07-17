import React, { useState, useEffect, useRef } from 'react'
import classnames from 'classnames'
import { Key, fetchApi } from '../utils'
import Filt from '../filt/command'

type CommandHelpProps = {
    nextArgs: string[],
    currentArg: number,
    help: string,
    description: string,
    availableCommands: string[],
}

type CommandResult = {
    "id": number,
    "command": string,
    "result": string,
}

type ResultProps = {
    results: CommandResult[],
}

function getAvailableCommands(commands: object, input: string = "") {
    if (!commands) return []
    let availableCommands: string[] = []
    for (const [command, args] of Object.entries(commands)) {
        if (command.startsWith(input)) {
            availableCommands.push(command)
        }
    }
    return availableCommands
}

export function Results({results}: ResultProps) {
    const resultElement= useRef<HTMLDivElement>(null!);

    useEffect(() => {
        if (resultElement) {
            resultElement.current.addEventListener('DOMNodeInserted', event => {
                const { currentTarget: target } = event;
                target.scroll({ top: target.scrollHeight, behavior: 'auto' });
            });
        }
    }, [])

    return (
        <div className="command-result" ref={resultElement}>
            {results.map(result => (
                <div key={result.id}>
                    <div><strong>$ {result.command}</strong></div>
                    {result.result}
                </div>
            ))}
        </div>
    )
}

export function CommandHelp({nextArgs, currentArg, help, description, availableCommands}: CommandHelpProps){
    let argumentSuggestion: JSX.Element[] = []
    for (let i: number = 0; i < nextArgs.length; i++) {
        if (i==currentArg) {
            argumentSuggestion.push(<mark>{nextArgs[i]}</mark>)
            continue
        }
        argumentSuggestion.push(<span>{nextArgs[i]} </span>)
    }
    return (<div className="argument-suggestion popover top">
        <div className="arrow"/>
        <div className="popover-content">
            { argumentSuggestion.length > 0 && <div><strong>Argument suggestion:</strong> {argumentSuggestion}</div> }
            { help?.includes("->") && <div><strong>Signature help: </strong>{help}</div>}
            { description && <div># {description}</div>}
            <div><strong>Available Commands: </strong><p className="available-commands">{JSON.stringify(availableCommands)}</p></div>
        </div>
    </div>)
}

export default function CommandBar() {
    const [input, setInput] = useState<string>("")
    const [originalInput, setOriginalInput] = useState<string>("")
    const [currentCompletion, setCurrentCompletion] = useState<number>(0)
    const [completionCandidate, setCompletionCandidate] = useState<string[]>([])

    const [availableCommands, setAvailableCommands] = useState<string[]>([])
    const [allCommands, setAllCommands] = useState<object>({})
    const [nextArgs, setNextArgs] = useState<string[]>([])
    const [currentArg, setCurrentArg] = useState<number>(0)
    const [signatureHelp, setSignatureHelp] = useState<string>("")
    const [description, setDescription] = useState<string>("")

    const [results, setResults] = useState<CommandResult[]>([])
    const [history, setHistory] = useState<string[]>([])
    const [currentPos, setCurrentPos] = useState<number>(0)

    useEffect(() => {
        fetchApi('/commands', { method: 'GET' })
        .then(response => response.json())
        .then(data => {
            setAllCommands(data["commands"])
            setCompletionCandidate(getAvailableCommands(data["commands"]))
            setAvailableCommands(Object.keys(data["commands"]))
        })
    }, [])

    const parseCommand = (originalInput: string, input: string) => {
        const parts: string[] = Filt.parse(input)
        const originalParts: string[] = Filt.parse(originalInput)

        setSignatureHelp(allCommands[parts[0]]?.signature_help)
        setDescription(allCommands[parts[0]]?.description)

        setCompletionCandidate(getAvailableCommands(allCommands, originalParts[0]))
        setAvailableCommands(getAvailableCommands(allCommands, parts[0]))

        const nextArgs: string[] = allCommands[parts[0]]?.args

        if (nextArgs) {
            setNextArgs([parts[0], ...nextArgs])
            setCurrentArg(parts.length-1)
        }
    }

    const onChange = (e) =>  {
        setInput(e.target.value)
        setOriginalInput(e.target.value)
        setCurrentCompletion(0)
    }

    const onKeyDown = (e) => {
        if (e.keyCode === Key.ENTER) {
            const body = {"command": input}

            fetchApi(`/commands`, {
                method: 'POST',
                body: JSON.stringify(body),
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                setHistory(data.history)
                setCurrentPos(currentPos + 1)
                setNextArgs([])
                setResults([...results, {
                    "id": results.length,
                    "command": input,
                    "result": JSON.stringify(data.result)
                }])
            })

            setSignatureHelp("")
            setDescription("")

            setInput("")
            setOriginalInput("")

            setCurrentCompletion(0)
            setCompletionCandidate(availableCommands)
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
            setInput(completionCandidate[currentCompletion])
            setCurrentCompletion((currentCompletion + 1) % completionCandidate.length)
            e.preventDefault()
        }
        e.stopPropagation()
    }

    const onKeyUp = (e) => {
        if (!input) {
            setAvailableCommands(Object.keys(allCommands))
            return
        }
        parseCommand(originalInput, input)
        e.stopPropagation()
    }

    return (
        <div className="command">
            <div className="command-title">
                Command Result
            </div>
            <Results results={results} />
            <CommandHelp nextArgs={nextArgs} currentArg={currentArg} help={signatureHelp} description={description} availableCommands={availableCommands} />
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
        </div>
    )
}