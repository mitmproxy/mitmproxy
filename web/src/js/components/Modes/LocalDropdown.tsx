import * as React from "react";
import { LocalState } from "../../modes/local";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { setSelectedProcesses } from "../../ducks/modes/local";
import { Popover } from "./Popover";
import { fetchProcesses, Process } from "../../ducks/processes";
import { rpartition } from "../../utils";

interface LocalDropdownProps {
    server: LocalState;
}

export default function LocalDropdown({ server }: LocalDropdownProps) {
    const { currentProcesses, isLoading } = useAppSelector(
        (state) => state.processes,
    );

    const { selectedProcesses } = useAppSelector(
        (state) => state.modes.local[0],
    );

    const [filteredProcesses, setFilteredProcesses] = React.useState<Process[]>(
        [],
    );

    const [currentSearch, setCurrentSearch] = React.useState("");

    const dispatch = useAppDispatch();

    const { platform } = useAppSelector((state) => state.backendState);

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setCurrentSearch(e.target.value);
    };

    const extractProcessName = (process: Process) => {
        // we cannot use directly the display_name because it is exposed by every executable and it might lead to unexpected results
        const separator = platform.startsWith("win32") ? "\\" : "/";
        return rpartition(process.executable, separator)[1];
    };

    // This function can take a Process in the case of the dropdown list or a string in the case of the input field when we want to add a process which is not in the list
    const addProcessToSelection = (option: Process | string) => {
        const processName =
            typeof option === "string" ? option : extractProcessName(option);

        const newSelectedProcesses = selectedProcesses
            ? `${selectedProcesses}, ${processName}`
            : processName;

        dispatch(setSelectedProcesses({ server, value: newSelectedProcesses }));
    };

    const removeProcessFromSelection = (option: Process) => {
        const newSelectedProcesses = selectedProcesses
            ?.split(/,\s*/)
            .filter((app) => app !== extractProcessName(option))
            .join(", ");

        dispatch(setSelectedProcesses({ server, value: newSelectedProcesses }));
    };

    const handleApplicationClick = (option: Process) => {
        if (isSelected(option) && selectedProcesses) {
            removeProcessFromSelection(option);
        } else {
            addProcessToSelection(option);
        }
    };

    const isSelected = (option: Process) => {
        const processName = extractProcessName(option);
        return selectedProcesses?.includes(processName);
    };

    React.useEffect(() => {
        if (currentProcesses.length === 0) dispatch(fetchProcesses());
    }, []);

    React.useEffect(() => {
        if (currentSearch) {
            const filtered = currentProcesses.filter((option) =>
                extractProcessName(option)
                    .toLowerCase()
                    .includes(currentSearch.toLowerCase()),
            );
            setFilteredProcesses(filtered);
        } else if (filteredProcesses !== currentProcesses) {
            setFilteredProcesses(currentProcesses);
        }
    }, [currentSearch, currentProcesses]);

    const handleInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        e.stopPropagation();
        if (e.key === "Enter") {
            addProcessToSelection(currentSearch);
            setCurrentSearch("");
        }
    };

    const [isPopoverVisible, setPopoverVisible] = React.useState(false);

    return (
        <div className="local-dropdown">
            <div className="dropdown-header">
                <input
                    type="text"
                    className="autocomplete-input"
                    placeholder={
                        selectedProcesses && selectedProcesses?.length > 0
                            ? "Add more"
                            : "all applications"
                    }
                    value={currentSearch}
                    onChange={handleInputChange}
                    onKeyDown={handleInputKeyDown}
                    onClick={() => setPopoverVisible(true)}
                    onBlur={() => setPopoverVisible(false)}
                />
                <Popover
                    iconClass="fa fa-chevron-down"
                    classname="local-popover"
                    isVisible={isPopoverVisible}
                >
                    <h4>Current Applications running on machine</h4>
                    {isLoading ? (
                        <i className="fa fa-spinner" aria-hidden="true"></i>
                    ) : filteredProcesses.length > 0 ? (
                        <ul className="dropdown-list">
                            <li
                                className={`dropdown-item ${selectedProcesses === "" ? "selected" : ""}`}
                                onClick={() => {
                                    dispatch(
                                        setSelectedProcesses({
                                            server,
                                            value: "",
                                        }),
                                    );
                                }}
                                role="menuitem"
                            >
                                <div className="process-details">
                                    <div className="process-icon" />
                                    <span className="process-name">
                                        All applications
                                    </span>
                                </div>
                                {selectedProcesses === "" && (
                                    <i
                                        className="fa fa-check"
                                        aria-hidden="true"
                                    />
                                )}
                            </li>
                            <hr className="process-separator" />
                            {filteredProcesses.map((option, index) => (
                                <li
                                    key={index}
                                    className={`dropdown-item ${isSelected(option) ? "selected" : ""}`}
                                    onClick={() =>
                                        handleApplicationClick(option)
                                    }
                                    role="menuitem"
                                >
                                    <div className="process-details">
                                        <img
                                            className="process-icon"
                                            src={`./executable-icon?path=${option.executable}`}
                                            loading="lazy"
                                        />
                                        <span className="process-name">
                                            {extractProcessName(option)}
                                        </span>
                                    </div>
                                    {isSelected(option) && (
                                        <i
                                            className="fa fa-check"
                                            aria-hidden="true"
                                        />
                                    )}
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <span>
                            Press <strong>Enter</strong> to capture traffic for
                            programs matching: <strong>{currentSearch}</strong>
                        </span>
                    )}
                </Popover>
            </div>
        </div>
    );
}
