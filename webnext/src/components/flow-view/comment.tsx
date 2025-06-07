import type { TabProps } from "@/components/flow-view/panel-tabs";
import { Section, SectionTitle } from "@/components/flow-view/section";
import { Textarea } from "@/components/ui/textarea";
import { useDebounceCallback } from "usehooks-ts";
import { update } from "web/ducks/flows";
import { useAppDispatch } from "web/ducks/hooks";

export function Comment({ flow }: TabProps) {
  const dispatch = useAppDispatch();

  const updateComment = useDebounceCallback((comment: string) => {
    void dispatch(update(flow, { comment }));
  }, 500);

  return (
    <Section>
      <SectionTitle>Comment</SectionTitle>
      <Textarea
        placeholder="Add your comment"
        defaultValue={flow.comment}
        onChange={(e) => updateComment(e.target.value)}
      />
    </Section>
  );
}
