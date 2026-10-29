import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("M0 scope shell", () => {
  it("discloses scope and provides a usable validation command", () => {
    const html = renderToStaticMarkup(<App />);
    expect(html).toContain("simready data validate --scene data/scenes/redwood");
    expect(html).toContain("are not implemented");
    expect(html).toContain("does not connect to a backend");
    expect(html).not.toContain("<button");
  });
});
