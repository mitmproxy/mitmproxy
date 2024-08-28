import * as React from "react";

export default function LocalDropdown() {
    const currentExecutables = [
        "curl",
        "wget",
        "python",
        "java",
        "node",
        "npm",
        "yarn",
        "pip",
        "ruby",
        "gem",
        "docker",
        "docker-compose",
        "kubectl",
    ];
    const [selectedExecutables, setSelectedExecutables] = React.useState<
        string[]
    >([]);
    const [isDropdownOpen, setIsDropdownOpen] = React.useState(false);

    const toggleDropdown = () => {
        setIsDropdownOpen(!isDropdownOpen);
    };

    const handleExecutableClick = (option) => {
        if (selectedExecutables.includes(option)) {
            setSelectedExecutables(
                selectedExecutables.filter((item) => item !== option),
            );
        } else {
            setSelectedExecutables([...selectedExecutables, option]);
        }
    };

    const isSelected = (executable) => selectedExecutables.includes(executable);

    return (
        <div className="multi-select-dropdown">
            <div className="dropdown-header" onClick={toggleDropdown}>
                <div className="selected-executables">
                    {selectedExecutables.length > 0
                        ? selectedExecutables.map((executable, index) => {
                              return (
                                  <span
                                      key={index}
                                      className="selected-executable"
                                  >
                                      {executable}
                                  </span>
                              );
                          })
                        : "Select executables"}
                </div>
                <span className={`arrow ${isDropdownOpen ? "up" : "down"}`} />
            </div>

            {isDropdownOpen && (
                <ul className="dropdown-list">
                    {currentExecutables.map((option, index) => (
                        <li
                            key={index}
                            className={`dropdown-item ${isSelected(option) ? "selected" : ""}`}
                            onClick={() => handleExecutableClick(option)}
                        >
                            {option}
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}
