import { describe, expect, it } from "vitest";
import { viewFromSearch } from "./WorkbenchNav";

describe("workbench deep links", () => {
  it("restores known views and rejects unknown query values", () => {
    expect(viewFromSearch("?view=research")).toBe("research");
    expect(viewFromSearch("?view=evaluation")).toBe("evaluation");
    expect(viewFromSearch("?view=unknown")).toBe("3d");
    expect(viewFromSearch("?other=research")).toBe("3d");
  });
});
