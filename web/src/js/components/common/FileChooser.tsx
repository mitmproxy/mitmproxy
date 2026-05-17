import React from "react";

type FileChooserProps = {
    icon: string;
    text?: string;
    className?: string;
    title?: string;
    onOpenFile: (file: File) => void;
    onClick?: (e: React.MouseEvent<HTMLAnchorElement>) => void;
};

export default React.memo(function FileChooser({
    icon,
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
            <i className={"fa fa-fw " + icon} />
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
