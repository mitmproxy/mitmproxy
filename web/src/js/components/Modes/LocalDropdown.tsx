import * as React from "react";
import { LocalState, Process } from "../../modes/local";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { setSelectedApplications } from "../../ducks/modes/local";
import { Popover } from "./Popover";
import { fetchApi } from "../../utils";

interface LocalDropdownProps {
    server: LocalState;
    isRefreshing: boolean;
}

export default function LocalDropdown({
    server,
    isRefreshing,
}: LocalDropdownProps) {
    const [currentApplications, setCurrentApplications] = React.useState<
        Process[]
    >([]);

    const selectedApplications = useAppSelector(
        (state) => state.modes.local[0].selectedApplications,
    );

    const [filteredApplications, setFilteredApplications] = React.useState<
        Process[]
    >([]);

    const [currentSearch, setCurrentSearch] = React.useState("");

    const dispatch = useAppDispatch();

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setCurrentSearch(e.target.value);
    };

    const handleApplicationClick = (option: Process) => {
        if (isSelected(option) && selectedApplications) {
            const newSelectedApplications = selectedApplications
                .split(", ")
                .filter((app) => app !== option.display_name)
                .join(", ");

            dispatch(
                setSelectedApplications({
                    server,
                    value: newSelectedApplications,
                }),
            );
            return;
        }

        const newSelectedApplications = selectedApplications
            ? `${selectedApplications}, ${option.display_name}`
            : option.display_name;

        dispatch(
            setSelectedApplications({ server, value: newSelectedApplications }),
        );
    };

    const isSelected = (option: Process) => {
        return selectedApplications?.includes(option.display_name);
    };

    React.useEffect(() => {
        fetchApi("/processes")
            .then((response) => response.json())
            .then((data) => setCurrentApplications(data))
            .catch((err) => console.error(err));
    }, [isRefreshing]);

    React.useEffect(() => {
        if (currentSearch) {
            const filtered = currentApplications.filter((option) =>
                option.display_name
                    .toLowerCase()
                    .includes(currentSearch.toLowerCase()),
            );
            setFilteredApplications(filtered);
        } else if (filteredApplications !== currentApplications) {
            setFilteredApplications(currentApplications);
        }
    }, [currentSearch, currentApplications]);

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
                    placeholder="Search Applications"
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
                    {filteredApplications.length > 0 ? (
                        <ul className="dropdown-list">
                            {filteredApplications.map((option, index) => (
                                <li
                                    key={index}
                                    className="dropdown-item"
                                    onClick={() =>
                                        handleApplicationClick(option)
                                    }
                                    role="menuitem"
                                >
                                    <span className="icon-container">
                                        {isSelected(option) && (
                                            <i
                                                className="fa fa-check check-icon"
                                                aria-hidden="true"
                                            />
                                        )}
                                    </span>
                                    <div className="application-details">
                                        <span className="application-icon">
                                            {option.icon}
                                        </span>
                                        <span className="application-name">
                                            {option.display_name}
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
