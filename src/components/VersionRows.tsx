import { ButtonItem, Field } from "@decky/ui";
import type { LibraryRowView } from "../presentation/library";

/** Version rows in a dialog: a row with an action is a button, the rest are plain text the gamepad skips. */
export function VersionRows({ rows, onAction }: { rows: LibraryRowView[]; onAction: (id: string, label: string) => void }) {
  return (
    <>
      {rows.map((row) =>
        row.action ? (
          <ButtonItem
            key={row.id}
            label={row.label}
            description={row.description}
            disabled={!row.action.enabled}
            onClick={() => onAction(row.id, row.label)}
          >
            {row.action.label}
          </ButtonItem>
        ) : (
          <Field key={row.id} label={row.label} description={row.description} />
        ),
      )}
    </>
  );
}
