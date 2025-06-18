import type { TabProps } from "@/components/flow-view/panel-tabs";
import { Section, SectionTitle } from "@/components/flow-view/section";
import { Textarea } from "@/components/ui/textarea";
import { useDebouncedCallback } from "use-debounce";
import { useState, useEffect } from "react";
import { update } from "web/ducks/flows";
import { useAppDispatch } from "web/ducks/hooks";

export function Comment({ flow }: TabProps) {
  const dispatch = useAppDispatch();
  const [comment, setComment] = useState(flow.comment);
  const debouncedUpdate = useDebouncedCallback((value: string) => {
    void dispatch(update(flow, { comment: value }));
  }, 250);

  // Update the local state when the parent passes down a new comment.
  useEffect(() => {
    setComment(flow.comment);
  }, [flow.comment]);

  const changeComment = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setComment(value);
    debouncedUpdate(value);
  };

  return (
    <Section>
      <SectionTitle>Comment</SectionTitle>
      <Textarea
        placeholder="Add your comment"
        value={comment}
        onChange={changeComment}
      />
    </Section>
  );
}
