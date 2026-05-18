import { useState, type ReactNode } from "react";
import { RailSection } from "../../ui/RailSection";

type Props = {
  phone: ReactNode;
  debate: ReactNode;
};

export function ToolsRail({ phone, debate }: Props) {
  const [open, setOpen] = useState(false);
  return (
    <RailSection title="Tools" testId="tools-rail">
      <button
        type="button"
        className="tools-rail__toggle"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        {open ? "Hide phone & debate" : "Phone & debate"}
      </button>
      {open && (
        <div className="tools-rail__body">
          {phone}
          {debate}
        </div>
      )}
    </RailSection>
  );
}
