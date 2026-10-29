import demoPreview from "../../src/simready/demo/analytic-plane/renders/frame_00006.png";

export function App() {
  return (
    <main>
      <header><span className="mark">S</span><strong>SimReady</strong><span className="badge">M1 · Reconstruction</span></header>
      <section>
        <p className="eyebrow">Perception-validated Real2Sim · development shell</p>
        <h1>Reliable scenes start<br />with reliable inputs.</h1>
        <p className="intro">The foundation now includes validated RGB-D inputs and a working Gaussian reconstruction pipeline. Use the local CLI to import, train, reload and render a scene.</p>
      </section>
      <div className="panels">
        <article>
          <h2>Available through the CLI</h2>
          <ul><li>Real TUM RGB-D import with supplied poses</li><li>Calibration, depth and frozen split validation</li><li>Isolated gsplat training and RGB/depth rendering</li><li>CPU smoke using a genuinely trained analytic model</li></ul>
          <pre>simready data validate --scene data/scenes/tum-fr1-desk<br />simready recon smoke</pre>
        </article>
        <article>
          <h2>Planned after M1</h2>
          <p>The 3D editor, perception evaluation, simulation and review workflows are not implemented.</p>
          <p>This shell is a scope overview. It does not connect to a backend or display scene data.</p>
        </article>
      </div>
      <figure className="demo-preview">
        <img src={demoPreview} alt="Saved view from a genuinely trained analytic synthetic plane" />
        <figcaption>Saved Gaussian render · analytic synthetic fixture · CC0<br />Bundled CPU preview; live rendering requires the separate GPU worker.</figcaption>
      </figure>
      <footer>Data and reconstruction foundations · Scene quality and perception remain unmeasured</footer>
    </main>
  );
}
