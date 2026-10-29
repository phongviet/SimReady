import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("current scope shell", () => {
  it("discloses scope and provides a usable validation command", () => {
    const html = renderToStaticMarkup(<App />);
    expect(html).toContain("simready data validate --scene data/scenes/tum-fr1-desk");
    expect(html).toContain("simready recon smoke");
    expect(html).toContain("are not implemented");
    expect(html).toContain("does not connect to a backend");
    expect(html).not.toContain("<button");
  });
});
