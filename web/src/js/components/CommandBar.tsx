import React, { useEffect, useRef, useState } from "react";
import classnames from "classnames";
import { fetchApi, runCommand } from "../utils";
import Filt from "../filt/command";

type CommandParameter = {
    name: string;
    type: string;
    kind: string;
};

type Command = {
    help?: string;
    parameters: CommandParameter[];
    return_type: string | undefined;
    signature_help: string;
};

type AllCommands = {
    [name: string]: Command;
};

type CommandHelpProps = {
    nextArgs: string[];
    currentArg: number;
    help: string;
    description: string;
    availableCommands: string[];
};

type CommandResult = {
    command: string;
    result: string;
};

type ResultProps = {
    results: CommandResult[];
};

function getAvailableCommands(
    commands: AllCommands,
    input: string = "",
): string[] {
    if (!commands) return [];
    const availableCommands: string[] = [];
    for (const command of Object.keys(commands)) {
        if (command.startsWith(input)) {
            availableCommands.push(command);
        }
    }
    return availableCommands;
}

export function Results({ results }: ResultProps) {
    const resultElement = useRef<HTMLDivElement>(null!);

    useEffect(() => {
        if (resultElement) {
            resultElement.current.addEventListener(
                "DOMNodeInserted",
                (event) => {
                    const target = event.currentTarget as Element;
                    target.scroll({
                        top: target.scrollHeight,
                        behavior: "auto",
                    });
                },
            );
        }
    }, []);

    return (
        <div className="command-result" ref={resultElement}>
            {results.map((result, i) => (
                <div key={i}>
                    <div>
                        <strong>$ {result.command}</strong>
                    </div>
                    {result.result}
                </div>
            ))}
        </div>
    );
}

export function CommandHelp({
    nextArgs,
    currentArg,
    help,
    description,
    availableCommands,
}: CommandHelpProps) {
    const argumentSuggestion: JSX.Element[] = [];
    for (let i: number = 0; i < nextArgs.length; i++) {
        if (i == currentArg) {
            argumentSuggestion.push(<mark key={i}>{nextArgs[i]}</mark>);
            continue;
        }
        argumentSuggestion.push(<span key={i}>{nextArgs[i]} </span>);
    }
    return (
        <div className="argument-suggestion popover top">
            <div className="arrow" />
            <div className="popover-content">
                {argumentSuggestion.length > 0 && (
                    <div>
                        <strong>Argument suggestion:</strong>{" "}
                        {argumentSuggestion}
                    </div>
                )}
                {help?.includes("->") && (
                    <div>
                        <strong>Signature help: </strong>
                        {help}
                    </div>
                )}
                {description && <div># {description}</div>}
                <div>
                    <strong>Available Commands: </strong>
                    <p className="available-commands">
                        {JSON.stringify(availableCommands)}
                    </p>
                </div>
            </div>
        </div>
    );
}

export default function CommandBar() {
    const [input, setInput] = useState<string>("");
    const [originalInput, setOriginalInput] = useState<string>("");
    const [currentCompletion, setCurrentCompletion] = useState<number>(0);
    const [completionCandidate, setCompletionCandidate] = useState<string[]>(
        [],
    );

    const [availableCommands, setAvailableCommands] = useState<string[]>([]);
    const [allCommands, setAllCommands] = useState<AllCommands>({});
    const [nextArgs, setNextArgs] = useState<string[]>([]);
    const [currentArg, setCurrentArg] = useState<number>(0);
    const [signatureHelp, setSignatureHelp] = useState<string>("");
    const [description, setDescription] = useState<string>("");

    const [results, setResults] = useState<CommandResult[]>([]);
    const [history, setHistory] = useState<string[]>([]);
    const [currentPos, setCurrentPos] = useState<number | undefined>(undefined);

    useEffect(() => {
        fetchApi("/commands", { method: "GET" })
            .then((response) => response.json())
            .then((data: AllCommands) => {
                setAllCommands(data);
                setCompletionCandidate(getAvailableCommands(data));
                setAvailableCommands(Object.keys(data));
            })
            .catch((e) => console.error(e));
    }, []);

    useEffect(() => {
        runCommand("commands.history.get")
            .then((ret) => {
                setHistory(ret.value);
            })
            .catch((e) => console.error(e));
    }, []);

    const parseCommand = (originalInput: string, input: string) => {
        const parts: string[] = Filt.parse(input);
        const originalParts: string[] = Filt.parse(originalInput);

        setSignatureHelp(allCommands[parts[0]]?.signature_help);
        setDescription(allCommands[parts[0]]?.help || "");

        setCompletionCandidate(
            getAvailableCommands(allCommands, originalParts[0]),
        );
        setAvailableCommands(getAvailableCommands(allCommands, parts[0]));

        const nextArgs: string[] = allCommands[parts[0]]?.parameters.map(
            (p) => p.name,
        );

        if (nextArgs) {
            setNextArgs([parts[0], ...nextArgs]);
            setCurrentArg(parts.length - 1);
        }
    };

    const onChange = (e) => {
        setInput(e.target.value);
        setOriginalInput(e.target.value);
        setCurrentCompletion(0);
    };

    const onKeyDown = (e) => {
        if (e.key === "Enter") {
            const [cmd, ...args] = Filt.parse(input);

            setHistory([...history, input]);
            runCommand("commands.history.add", input).catch(() => 0);

            fetchApi
                .post(`/commands/${cmd}`, { arguments: args })
                .then((response) => response.json())
                .then((data) => {
                    setCurrentPos(undefined);
                    setNextArgs([]);
                    setResults([
                        ...results,
                        {
                            command: input,
                            result: JSON.stringify(data.value || data.error),
                        },
                    ]);
                })
                .catch((e) => {
                    setCurrentPos(undefined);
                    setNextArgs([]);
                    setResults([
                        ...results,
                        {
                            command: input,
                            result: e.toString(),
                        },
                    ]);
                });

            setSignatureHelp("");
            setDescription("");

            setInput("");
            setOriginalInput("");

            setCurrentCompletion(0);
            setCompletionCandidate(availableCommands);
        }
        if (e.key === "ArrowUp") {
            let nextPos;
            if (currentPos === undefined) {
                nextPos = history.length - 1;
            } else {
                nextPos = Math.max(0, currentPos - 1);
            }
            setInput(history[nextPos]);
            setOriginalInput(history[nextPos]);
            setCurrentPos(nextPos);
        }
        if (e.key === "ArrowDown") {
            if (currentPos === undefined) {
                return;
            } else if (currentPos == history.length - 1) {
                setInput("");
                setOriginalInput("");
                setCurrentPos(undefined);
            } else {
                const nextPos = currentPos + 1;
                setInput(history[nextPos]);
                setOriginalInput(history[nextPos]);
                setCurrentPos(nextPos);
            }
        }
        if (e.key === "Tab") {
            setInput(completionCandidate[currentCompletion]);
            setCurrentCompletion(
                (currentCompletion + 1) % completionCandidate.length,
            );
            e.preventDefault();
        }
        e.stopPropagation();
    };

    const onKeyUp = (e) => {
        if (!input) {
            setAvailableCommands(Object.keys(allCommands));
            return;
        }
        parseCommand(originalInput, input);
        e.stopPropagation();
    };

    return (
        <div className="command">
            <div className="command-title">Command Result</div>
            <Results results={results} />
            <CommandHelp
                nextArgs={nextArgs}
                currentArg={currentArg}
                help={signatureHelp}
                description={description}
                availableCommands={availableCommands}
            />
            <div className={classnames("command-input input-group")}>
                <span className="input-group-addon">
                    <i className={"fa fa-fw fa-terminal"} />
                </span>
                <input
                    type="text"
                    placeholder="Enter command"
                    className="form-control"
                    value={input || ""}
                    onChange={onChange}
                    onKeyDown={onKeyDown}
                    onKeyUp={onKeyUp}
                />
            </div>
        </div>
    );
}
