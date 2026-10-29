import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { App } from "./App";
describe("studio startup", () => {
  it("shows a connection state before the local API responds", () => {
    const html = renderToStaticMarkup(<App />);
    expect(html).toContain("Connect your local studio");
    expect(html).toContain("simready api serve --demo");
    expect(html).not.toContain("approved");
  });
});
