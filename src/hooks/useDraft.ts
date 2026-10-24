import { useEffect, useState } from "react";

/** Text being typed over a stored value: follows the value when it changes, and is committed only when
 *  it differs from it (on leaving the field), so one edit is one save. */
export const useDraft = (value: string, commit: (text: string) => void) => {
  const [draft, setDraft] = useState(value);
  useEffect(() => setDraft(value), [value]);
  const onCommit = () => {
    if (draft !== value) commit(draft);
  };
  return { draft, setDraft, onCommit };
};
