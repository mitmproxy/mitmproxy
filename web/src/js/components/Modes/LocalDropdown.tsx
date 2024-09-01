import * as React from "react";
import { LocalState, Process } from "../../modes/local";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { setSelectedApplications } from "../../ducks/modes/local";

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

    const [isDropdownOpen, setIsDropdownOpen] = React.useState(false);

    const dispatch = useAppDispatch();

    const toggleDropdown = () => {
        setIsDropdownOpen(!isDropdownOpen);
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
        //call the endpoint to extract the list of applications and the icons
        setCurrentApplications([
            {
                is_visible: true,
                executable: "curl.exe",
                is_system: "false",
                display_name: "curl",
            },
            {
                is_visible: true,
                executable: "chrome.exe",
                is_system: "false",
                display_name: "Google Chrome",
            },
            {
                is_visible: false,
                executable: "svchost.exe",
                is_system: "true",
                display_name: "Service Host",
            },
            {
                is_visible: true,
                executable: "explorer.exe",
                is_system: "false",
                display_name: "File Explorer",
            },
            {
                is_visible: true,
                executable: "cmd.exe",
                is_system: "false",
                display_name: "Command Prompt",
            },
            {
                is_visible: false,
                executable: "winlogon.exe",
                is_system: "true",
                display_name: "Windows Logon Application",
            },
        ]);
    }, [isRefreshing]);

    return (
        <div className="local-dropdown">
            <div className="dropdown-header" onClick={toggleDropdown}>
                <div className="selected-executables">Select Executables</div>
                <span className={`arrow ${isDropdownOpen ? "up" : "down"}`} />
            </div>

            {isDropdownOpen && (
                <ul className="dropdown-list">
                    {currentApplications.map((option, index) => (
                        <li
                            key={index}
                            className="dropdown-item"
                            onClick={() => handleApplicationClick(option)}
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
            )}
        </div>
    );
}
