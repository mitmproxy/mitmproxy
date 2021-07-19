import React, { useEffect, useState } from 'react'
import { setContentViewDescription, setContent } from '../../ducks/ui/flow'
import withContentLoader from './ContentLoader'
import { MessageUtils } from '../../flow/utils'
import CodeEditor from './CodeEditor'
import { useAppDispatch, useAppSelector } from "../../ducks";


const isImage = /^image\/(png|jpe?g|gif|webp|vnc.microsoft.icon|x-icon)$/i
ViewImage.matches = msg => isImage.test(MessageUtils.getContentType(msg))

type ViewImageProps = {
    flow: object,
    message: object,
}

function ViewImage({ flow, message }: ViewImageProps) {
    return (
        <div className="flowview-image">
            <img src={MessageUtils.getContentURL(flow, message)} alt="preview" className="img-thumbnail"/>
        </div>
    )
}

type EditProps = {
    content: string,
    onChange: (content: string) => any,
}

function PureEdit({ content, onChange }: EditProps) {
    return <CodeEditor content={content} onChange={onChange}/>
}
const Edit = withContentLoader(PureEdit)

type PureViewServerProps = {
    flow: object,
    message: object,
    content: string,
}

type PureViewServerStates = {
    lines: [style: string, text: string][][],
    description: string,
}

export function PureViewServer({flow, message, content}: PureViewServerProps) {
    const [data, setData] = useState<PureViewServerStates>({
        lines: [],
        description: "",
    })

    const dispatch = useAppDispatch(),
    showFullContent: boolean = useAppSelector(state => state.ui.flow.showFullContent),
    maxLines: number = useAppSelector(state => state.ui.flow.maxContentLines)

    let lines = showFullContent ? data.lines : data.lines?.slice(0, maxLines)

    useEffect(() => {
        setContentView({flow, message, content})
    }, [flow, message, content])

    const setContentView = (props) => {
        try {
            setData(JSON.parse(props.content))
        }catch(err) {
            setData({lines: [], description: err.message})
        }

        dispatch(setContentViewDescription(props.contentView !== data.description ? data.description : ''))
        dispatch(setContent(data.lines))
    }

    return (
        <div>
            {ViewImage.matches(message) && <ViewImage flow={flow} message={message}/>}
            <pre>
                {lines.map((line, i) =>
                    <div key={`line${i}`}>
                        {line.map((element, j) => {
                            let [style, text] = element
                            return (
                                <span key={`tuple${j}`} className={style}>
                                    {text}
                                </span>
                            )
                        })}
                    </div>
                )}
            </pre>
        </div>
    )

}

const ViewServer = withContentLoader(PureViewServer)

export { Edit, ViewServer, ViewImage }
