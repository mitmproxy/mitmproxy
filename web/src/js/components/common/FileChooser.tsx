import React from "react";
import Icon from "./Icon";
import type { IconName } from "./Icon";

type FileChooserProps = {
    icon: IconName;
    iconClassName?: string;
    text?: string;
    className?: string;
    title?: string;
    onOpenFile: (File) => void;
    onClick?: (MouseEvent) => void;
};

export default React.memo(function FileChooser({
    icon,
    iconClassName,
    text,
    className,
    title,
    onOpenFile,
    onClick,
}: FileChooserProps) {
    let fileInput;
    return (
        <a
            href="#"
            onClick={(e) => {
                fileInput.click();
                if (onClick) onClick(e);
            }}
            className={className}
            title={title}
        >
            <Icon name={icon} className={iconClassName} />
            &nbsp;
            {text}
            <input
                ref={(ref) => {
                    fileInput = ref;
                }}
                className="hidden"
                type="file"
                onChange={(e) => {
                    e.preventDefault();
                    if (e.target.files && e.target.files.length > 0)
                        onOpenFile(e.target.files[0]);
                    fileInput.value = "";
                }}
            />
        </a>
    );
});
