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

    const handleApplicationClick = (option: Process) => {
        if (isSelected(option) && selectedProcesses) {
            const newSelectedProcesses = selectedProcesses
                .split(", ")
                .filter((app) => app !== extractProcessName(option))
                .join(", ");

            dispatch(
                setSelectedProcesses({
                    server,
                    value: newSelectedProcesses,
                }),
            );
            return;
        }

        const newSelectedProcesses = selectedProcesses
            ? `${selectedProcesses}, ${extractProcessName(option)}`
            : extractProcessName(option);

        dispatch(setSelectedProcesses({ server, value: newSelectedProcesses }));
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
                            : "(all applications)"
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
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <span>No results</span>
                    )}
                </Popover>
            </div>
        </div>
    );
}
