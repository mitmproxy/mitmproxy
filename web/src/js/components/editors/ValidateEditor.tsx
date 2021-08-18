import React, {useRef, useState} from 'react'
import ValueEditor, {ValueEditorProps} from './ValueEditor'
import classnames from "classnames";

interface ValidateEditorProps extends ValueEditorProps {
    isValid: (content: string) => boolean,
}

export default function ValidateEditor(props: ValidateEditorProps) {
    const [isValid, setIsValid] = useState(props.isValid(props.content));
    const editor = useRef<ValueEditor>(null);

    const onChange = (newVal: string) => {
        if (props.isValid(newVal)) {
            props.onEditDone(newVal);
        } else {
            editor.current?.cancelEditing();
        }
    }

    const className = classnames(props.className, isValid ? 'has-success' : 'has-warning');
    return <ValueEditor
        {...props}
        className={className}
        onInput={newVal => setIsValid(props.isValid(newVal))}
        onEditDone={onChange}
        ref={editor}
    />
}
