import React from "react";

type FileChooserProps = {
    icon: string;
    text?: string;
    className?: string;
    title?: string;
    onOpenFile: (File) => void;
    onClick?: (MouseEvent) => void;
};

export default React.memo(function FileChooser({
    icon,
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
                    fileInput.value = "";
                }}
            />
        </a>
    );
});
