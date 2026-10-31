import * as Tooltip from "@radix-ui/react-tooltip";
import { Button } from "./components/ui/button";
export type WorkbenchView =
  "3d" | "saved" | "evaluation" | "simulation" | "review" | "research";
const destinations: {
  id: WorkbenchView;
  label: string;
  mark: string;
  group: string;
}[] = [
  {
    id: "3d",
    label: "3D scene",
    mark: "M3 7 12 3l9 4v10l-9 4-9-4V7Zm0 0 9 4 9-4M12 11v10",
    group: "Workspace",
  },
  {
    id: "saved",
    label: "Saved camera",
    mark: "M3 7h5l2-3h4l2 3h5v13H3V7Zm5 6a4 4 0 1 0 8 0 4 4 0 0 0-8 0",
    group: "Workspace",
  },
  {
    id: "evaluation",
    label: "Evaluation",
    mark: "M3 4h8v16H3V4Zm10 0h8v16h-8V4M6 15l2-3 2 3m6-5h2m-2 4h2",
    group: "Validation",
  },
  {
    id: "research",
    label: "Research",
    mark: "M4 3v18h17M8 16l4-7 4 3 5-7",
    group: "Experiments",
  },
  {
    id: "simulation",
    label: "Navigation",
    mark: "M4 19h6l4-14h6M3 16v6m14-20v6",
    group: "Simulation",
  },
  {
    id: "review",
    label: "Readiness / review",
    mark: "M12 3 3 7v6c0 4 9 8 9 8s9-4 9-8V7l-9-4Zm-5 9 3 3 7-7",
    group: "Review",
  },
];
export function WorkbenchNav({
  view,
  onView,
  collapsed,
  disabled,
}: {
  view: WorkbenchView;
  onView: (v: WorkbenchView) => void;
  collapsed: boolean;
  disabled: boolean;
}) {
  return (
    <Tooltip.Provider delayDuration={300}>
      <nav aria-label="Workbench views" className="workbench-nav">
        {destinations.map((item) => (
          <Tooltip.Root key={item.id}>
            <Tooltip.Trigger asChild>
              <Button
                variant="ghost"
                disabled={disabled}
                aria-label={item.label}
                aria-current={view === item.id ? "page" : undefined}
                onClick={() => onView(item.id)}
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  aria-hidden="true"
                >
                  <path d={item.mark} />
                </svg>
                {!collapsed && (
                  <span>
                    <small>{item.group}</small>
                    {item.label}
                  </span>
                )}
              </Button>
            </Tooltip.Trigger>
            <Tooltip.Portal>
              <Tooltip.Content
                className="wb-tooltip"
                side="right"
                sideOffset={8}
              >
                {item.label}
                <Tooltip.Arrow />
              </Tooltip.Content>
            </Tooltip.Portal>
          </Tooltip.Root>
        ))}
      </nav>
    </Tooltip.Provider>
  );
}
