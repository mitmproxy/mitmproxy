import React from "react";
import Icon from "./Icon";
import type { IconName } from "./Icon";

type FileChooserProps = {
    icon: IconName;
    iconClassName?: string;
    text?: string;
    className?: string;
    title?: string;
    onOpenFile: (file: File) => void;
    onClick?: (e: React.MouseEvent<HTMLAnchorElement>) => void;
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
    let fileInput: HTMLInputElement | null = null;
    return (
        <a
            href="#"
            onClick={(e) => {
                fileInput?.click();
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
                    if (fileInput) fileInput.value = "";
                }}
            />
        </a>
    );
});
