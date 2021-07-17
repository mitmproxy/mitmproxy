import React  from 'react'
import ViewSelector from './ViewSelector'
import UploadContentButton from './UploadContentButton'
import DownloadContentButton from './DownloadContentButton'
import { useAppSelector } from "../../ducks";

type ContentViewOptionsProps = {
    flow: object,
    message: object,
    uploadContent: () => void,
}

export default function ContentViewOptions({ flow, message, uploadContent }: ContentViewOptionsProps) {
    const contentViewDescription = useAppSelector(state => state.ui.flow.viewDescription)
    const readonly = useAppSelector(state => state.ui.flow.modifiedFlow);
    return (
        <div className="view-options">
            {readonly ? <ViewSelector /> : <span><b>View:</b> edit</span>}
            &nbsp;
            <DownloadContentButton flow={flow} message={message}/>
            &nbsp;
            {!readonly && <UploadContentButton uploadContent={uploadContent}/> }
            &nbsp;
            {readonly && <span>{contentViewDescription}</span>}
        </div>
    )
}
