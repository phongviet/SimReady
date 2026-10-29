export function App() {
  return (
    <main>
      <header><span className="mark">S</span><strong>SimReady</strong><span className="badge">M0 · Foundation</span></header>
      <section>
        <p className="eyebrow">Perception-validated Real2Sim · development shell</p>
        <h1>Reliable scenes start<br />with reliable inputs.</h1>
        <p className="intro">The first milestone establishes the RGB-D dataset contract and camera mathematics. Use the local CLI to import and validate a scene.</p>
      </section>
      <div className="panels">
        <article>
          <h2>Available through the CLI</h2>
          <ul><li>Analytic synthetic RGB-D fixture</li><li>Official Open3D sample import</li><li>Calibration, depth and pose validation</li><li>Frozen, disjoint dataset splits</li></ul>
          <pre>simready data validate --scene data/scenes/redwood</pre>
        </article>
        <article>
          <h2>Planned after M0</h2>
          <p>Reconstruction, the 3D editor, perception evaluation, simulation and review workflows are not implemented.</p>
          <p>This shell is a scope overview. It does not connect to a backend or display scene data.</p>
        </article>
      </div>
      <footer>CPU-only foundation · No reconstruction or experimental results claimed</footer>
    </main>
  );
}
