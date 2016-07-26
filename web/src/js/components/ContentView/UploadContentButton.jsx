import { PropTypes } from 'react'

UploadContentButton.propTypes = {
    uploadContent: PropTypes.func.isRequired,
}

export default function UploadContentButton({ uploadContent }) {

    let fileInput;

    return (
        <a className="btn btn-default btn-xs"
           onClick={() => fileInput.click()}
           title="Upload a file to replace the content.">
            <i className="fa fa-upload"/>
            <input
                ref={ref => fileInput = ref}
                className="hidden"
                type="file"
                onChange={e => {
                    if (e.target.files.length > 0) uploadContent(e.target.files[0])
                }}
            />
        </a>

    )
}

