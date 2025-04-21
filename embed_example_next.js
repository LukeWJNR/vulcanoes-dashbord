import Head from "next/head";

export default function ClimateVolcanoesPage() {
  return (
    <>
      <Head>
        <title>Climate & Volcanoes</title>
      </Head>
      <main style={{ padding: "2rem", maxWidth: "800px", margin: "auto", lineHeight: "1.6" }}>
        <h1>🌋 Climate Change & Volcanic Activity</h1>
        <p>
          This page explores the emerging link between climate change and geological instability,
          including volcanic eruptions and seismic events.
        </p>

        {/* Volcano Dashboard Embedding */}
        <h2>🔍 Interactive Volcano Dashboard</h2>
        <p>
          Explore this interactive dashboard showing active volcanoes around the world,
          their current status, eruption history, and potential climate impacts.
        </p>
        <div style={{ position: "relative", width: "100%", height: "600px", marginBottom: "2rem" }}>
          <iframe 
            src="YOUR_REPLIT_APP_URL?embed=true" 
            width="100%" 
            height="100%" 
            style={{ border: "none" }} 
            title="Volcano Monitoring Dashboard"
            allow="fullscreen"
          ></iframe>
        </div>

        <h2>📌 Case Study: Mayotte Underwater Volcano</h2>
        <p>
          In 2018, an underwater volcano was discovered near Mayotte after earthquake swarms and
          ground subsidence up to 12 cm/year. The eruption built an 800m-high seafloor structure in
          just six months — a stark reminder of the hidden risks beneath climate-impacted zones.
        </p>

        <h2>⛈️ Extreme Rainfall + Volcanism</h2>
        <p>
          Hawaii (Kilauea) in April 2018 broke rainfall records (1262mm in 24h) just weeks before a
          major eruption. Increased magma chamber pressure was recorded, and the eruption released
          massive SO₂ levels. Similar rainfall-volcano timing is seen in South America and
          Mediterranean regions.
        </p>

        {/* Lightweight 2D Eruption Visualization */}
        <h2>💻 Volcano Eruption Visualization</h2>
        <p>
          This lightweight visualization shows the eruption process for different volcano types,
          including magma chamber dynamics and eruption phases.
        </p>
        <div style={{ position: "relative", width: "100%", height: "700px", marginBottom: "2rem" }}>
          <iframe 
            src="YOUR_REPLIT_APP_URL/lightweight_2d_eruption?embed=true" 
            width="100%" 
            height="100%" 
            style={{ border: "none" }} 
            title="Volcano Eruption Visualization"
            allow="fullscreen"
          ></iframe>
        </div>

        <h2>🧱 Climate Impacts on Crustal Strain</h2>
        <ul>
          <li>🌊 Sea-level rise adds weight to oceanic plates → increased crustal strain</li>
          <li>🧊 Ice loss causes crustal rebound and shifting pressure zones</li>
          <li>🔥 Drought reduces surface mass → crust lifts and destabilizes faults</li>
          <li>🌧️ Floods shift sediment loads and change river basins → localized instability</li>
          <li>🌱 Soil erosion weakens upper crust → structural instability</li>
        </ul>

        <h2>🔗 Resources</h2>
        <ul>
          <li><a href="https://tsunami.gov" target="_blank" rel="noreferrer">Tsunami.gov</a></li>
          <li><a href="https://worldview.earthdata.nasa.gov" target="_blank" rel="noreferrer">NASA Worldview</a></li>
          <li><a href="https://volcano.si.edu/" target="_blank" rel="noreferrer">Smithsonian GVP</a></li>
        </ul>
      </main>
    </>
  );
}