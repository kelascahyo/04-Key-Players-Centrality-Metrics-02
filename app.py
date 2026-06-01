import streamlit as st
import pandas as pd
import networkx as nx
import json
import streamlit.components.v1 as components

# Set page configuration for a spacious, professional workspace
st.set_page_config(
    page_title="Tax Corporate Network Platform",
    page_icon="🕸️",
    layout="wide"
)

# Application Header
st.title("🕸️ Tax Corporate Network & Centrality Analysis Platform")
st.caption("An interactive network analytics engine engineered for tax investigators and compliance teams to expose holding groups and beneficial owners.")

# --- SIDEBAR CONFIGURATION AND AUDIT FILTERS ---
st.sidebar.header("📁 Control Panel & Data Filters")

@st.cache_data
def load_tax_data():
    try:
        # Explicitly read IDs as strings to prevent precision drop or leading zero truncation
        nodes = pd.read_csv("nodes_masked.csv", dtype={'id': str})
        edges = pd.read_csv("edges_masked_part1_a.csv", dtype={'sumber': str, 'target': str})
        
        # Clean whitespaces or formatting inconsistencies
        nodes['jenis_node'] = nodes['jenis_node'].str.strip()
        nodes['nama'] = nodes['nama'].str.strip()
        
        return nodes, edges
    except Exception as e:
        st.error(f"Fatal Error Loading CSV Files: {e}")
        return None, None

nodes_df, edges_df = load_tax_data()

if nodes_df is not None and edges_df is not None:
    
    st.sidebar.subheader("🔍 Network Density Filters")
    
    # 1. Scope Filter: Filter down by Node Type
    all_types = sorted(nodes_df['jenis_node'].dropna().unique().tolist())
    selected_types = st.sidebar.multiselect(
        "Include Taxpayer Categories:", 
        options=all_types, 
        default=all_types,
        help="Filter the visible ecosystem to specific legal entity classes."
    )
    
    # 2. Strength Filter: Filter down by ownership share weight
    min_share = st.sidebar.slider(
        "Minimum Shareholding Percentage (%)", 
        min_value=0.0, 
        max_value=100.0, 
        value=0.0, 
        step=1.0,
        help="Eliminate minor equity holdings to reveal the primary corporate structure."
    )
    
    # --- RIGOROUS DEFENSIVE GRAPH PRE-PROCESSING ---
    # Isolate valid node IDs belonging to the chosen entity types
    allowed_nodes_df = nodes_df[nodes_df['jenis_node'].isin(selected_types)]
    allowed_node_ids = set(allowed_nodes_df['id'].tolist())
    
    # Filter edges: percentage check AND both source & target must exist within chosen scope
    valid_edges_df = edges_df[
        (edges_df['persentase'] >= min_share) & 
        (edges_df['sumber'].isin(allowed_node_ids)) & 
        (edges_df['target'].isin(allowed_node_ids))
    ]
    
    # Identify unique node IDs that appear in our filtered edges
    active_edge_nodes = set(valid_edges_df['sumber'].tolist()).union(set(valid_edges_df['target'].tolist()))
    
    # Choose whether to show isolated (unconnected) taxpayers
    hide_isolated = st.sidebar.checkbox("Hide Isolated Nodes (Unconnected Taxpayers)", value=True)
    
    # Finalize the list of nodes to load into NetworkX
    if hide_isolated:
        final_nodes_df = allowed_nodes_df[allowed_nodes_df['id'].isin(active_edge_nodes)]
    else:
        final_nodes_df = allowed_nodes_df

    # Construct the Directed Network Matrix
    G = nx.DiGraph()
    
    for _, row in final_nodes_df.iterrows():
        G.add_node(row['id'], name=row['nama'], type=row['jenis_node'])
        
    for _, row in valid_edges_df.iterrows():
        G.add_edge(
            row['sumber'], row['target'], 
            weight=float(row['nilai']), 
            percentage=float(row['persentase']),
            dividend=float(row['dividen'])
        )
        
    # --- PERFORMANCE-OPTIMIZED CENTRALITY COMPUTATION ---
    # If network size is zero, build fallback defaults
    if len(G) > 0:
        out_degree = nx.out_degree_centrality(G)
        in_degree = nx.in_degree_centrality(G)
        
        # Performance optimization: Use a random sampling parameter k if the network is massive
        if len(G) > 1500:
            betweenness = nx.betweenness_centrality(G, k=150)
        else:
            betweenness = nx.betweenness_centrality(G)
    else:
        out_degree, in_degree, betweenness = {}, {}, {}
        
    # Inject computed scores back into NetworkX node attributes
    for node in G.nodes():
        G.nodes[node]['out_degree'] = out_degree.get(node, 0)
        G.nodes[node]['in_degree'] = in_degree.get(node, 0)
        G.nodes[node]['betweenness'] = betweenness.get(node, 0)

    # --- UI INTERFACE TABS ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "📖 Educational Guide & Overview", 
        "🕸️ Interactive D3.js Network View", 
        "📊 Centrality Metrics & Key Players", 
        "🔍 Taxpayer Lineage 360° Explorer"
    ])
    
    # ==================== TAB 1: EDUCATIONAL GUIDE ====================
    with tab1:
        st.markdown("""
## 📘 Educational Guide: Network Science in Corporate Taxation

Welcome to the Tax Network Analysis Platform. In corporate tax auditing, compliance management, and strategic investigations, business entities rarely operate in complete isolation. High-net-worth individuals (Conglomerates) and large multinational groups often establish intricate webs of cross-ownership, holding companies, shell structures, and special purpose vehicles to optimize taxes, transfer pricing, or mask the **Ultimate Beneficial Owner (UBO)**.

This application uses **Graph Theory (Network Science)** to transform traditional row-and-column tax reporting into a live structural roadmap, exposing the underlying power and flow of capital.

### 🧐 Core Structural Elements for Beginners

#### 1. Graph Components
* **Nodes (The Circles):** Represents an audited **Taxpayer (Wajib Pajak)**. In this dataset, nodes are classified into:
    * **Badan:** Domestic corporate entities or businesses operating within the country.
    * **OP (Orang Pribadi):** Individual taxpayers or natural persons (often the individual tycoons or company founders).
    * **LN (Luar Negeri):** Foreign/Offshore corporate entities. Monitoring these is critical for analyzing base erosion, profit shifting (BEPS), and international transfer pricing risk.
    * **Non NPWP:** Entities registered without a formal Tax Identification Number.
* **Edges (The Directed Arrows):** Represents a **Shareholding Relationship (Kepemilikan Saham)**. The arrow points from the **Investor (Sumber)** to the **Investee Company (Target)**, showing exactly where ownership control and capital investments flow.

#### 2. Network Centrality Metrics Explained
To discover the **"Key Players"** or major conglomerate centers within our corporate ecosystem, we measure three mathematical network parameters using NetworkX:

* **Out-Degree Centrality (Ownership Directives):**
    * *What it measures:* The proportion of outward ownership links emerging from a single node.
    * *Tax Auditing Significance:* A node with a high Out-Degree score is a highly active investor or ultimate parent company. This points directly to **Ultimate Conglomerates** or top-tier **Holding Companies** who sit at the absolute apex of massive corporate groups.
* **In-Degree Centrality (Capital Accumulation Load):**
    * *What it measures:* The number of inward equity links pointing toward a single node.
    * *Tax Auditing Significance:* A company with a high In-Degree score is a heavily funded operational entity or joint venture receiving capital from multiple stakeholders. These are key revenue hubs where business operations happen and profits accumulate.
* **Betweenness Centrality (The Corporate Bridges):**
    * *What it measures:* How frequently a specific node lies on the shortest structural pathways between all other pairs of nodes in the corporate ecosystem.
    * *Tax Meaning:* A high Betweenness score flags **Conduit Companies, Middlemen, or Intermediary Holding Structures**. If funds or dividends pass from a subsidiary to a parent entity across groups, they often pass through these bridge nodes. In risk mapping, these are high-priority structures for treaty shopping or dividend routing analysis.

---
### 📈 Current View Summary Statistics
""")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Taxpayers in View", f"{len(G):,}")
        col2.metric("Equity Relationships", f"{G.number_of_edges():,}")
        
        avg_links = (G.number_of_edges() / len(G)) if len(G) > 0 else 0
        col3.metric("Avg Ownership Links / Node", f"{avg_links:.2f}")
        
        if out_degree:
            max_out_id = max(out_degree, key=out_degree.get)
            max_out_name = G.nodes[max_out_id]['name']
            col4.metric("Top Group Parent Entity", f"ID: {max_out_id}", help=f"Name: {max_out_name}")
        else:
            col4.metric("Top Group Parent Entity", "N/A")

    # ==================== TAB 2: D3.JS INTERACTIVE MAP ====================
    with tab2:
        st.subheader("🕸️ Dynamic Network Topology Map (D3.js Rendering)")
        st.markdown("""
*Instructions:* Use your mouse scrollwheel to **zoom in/out** and click-and-drag empty spaces to **pan** across the digital map. 
**Hover** your mouse pointer over any colored circle to view registration details and centrality scores. **Drag** circles around to restructure the physics layout in real-time.
""")
        
        size_metric = st.selectbox(
            "Map Centrality Metric to Circle Size Scaling:",
            ["Out-Degree Centrality (Holding/Investor Influence)", 
             "In-Degree Centrality (Capital Injection Load)", 
             "Betweenness Centrality (Structural Bridge Indicator)"]
        )
        
        metric_key = "out_degree"
        if "In-Degree" in size_metric:
            metric_key = "in_degree"
        elif "Betweenness" in size_metric:
            metric_key = "betweenness"
            
        max_nodes_render = st.slider("Limit view to Top N central nodes to maintain smooth frame rates:", 20, 500, 150)
        
        if len(G) == 0:
            st.info("No nodes matching the current criteria to visualize.")
        else:
            # Sort and slice out the top nodes based on centrality
            sorted_nodes_list = sorted(G.nodes(data=True), key=lambda x: x[1].get(metric_key, 0), reverse=True)[:max_nodes_render]
            sliced_node_ids = set([n[0] for n in sorted_nodes_list])
            
            # CRITICAL FIX: Extract the exact induced subgraph so edges do NOT point to omitted nodes
            H = G.subgraph(sliced_node_ids)
            
            # Map node entries into a web-safe array
            d3_nodes = []
            for n_id, attrs in H.nodes(data=True):
                score = attrs.get(metric_key, 0)
                # Apply balanced dynamic size multipliers for the D3 frontend circles
                scaled_size = 6 + (score * 75) if metric_key != "betweenness" else 6 + (score * 250)
                
                d3_nodes.append({
                    "id": str(n_id),
                    "name": str(attrs.get('name', 'Unknown')),
                    "type": str(attrs.get('type', 'Badan')),
                    "score": round(float(score), 5),
                    "size": float(scaled_size)
                })
                
            # Map edge entries into a web-safe array
            d3_links = []
            for u, v, attrs in H.edges(data=True):
                d3_links.append({
                    "source": str(u),
                    "target": str(v),
                    "pct": float(attrs.get('percentage', 0)),
                    "val": float(attrs.get('weight', 0))
                })
                
            d3_payload = {"nodes": d3_nodes, "links": d3_links}
            d3_json_string = json.dumps(d3_payload)
            
            # COMPACT RE-ENGINEERED D3 HYBRID TEMPLATE
            html_code = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body { margin: 0; padding: 0; background-color: #1a1a24; font-family: sans-serif; color: #fff; overflow: hidden; }
                    #canvas-container { width: 100%; height: 620px; position: relative; }
                    .node-circle { stroke: #fff; stroke-width: 1.5px; cursor: pointer; }
                    .edge-line { stroke: #95a5a6; stroke-opacity: 0.4; stroke-width: 1.5px; fill: none; }
                    .arrow-tip { fill: #95a5a6; opacity: 0.5; }
                    .node-text { font-size: 10px; fill: #f3f3f3; pointer-events: none; text-shadow: 1px 1px 2px #000; }
                    .tax-tooltip { position: absolute; background: rgba(30, 41, 59, 0.95); border: 1px solid #38bdf8; border-radius: 6px; padding: 10px; font-size: 12px; display: none; pointer-events: none; box-shadow: 0 4px 10px rgba(0,0,0,0.5); z-index: 99; line-height: 1.4em; }
                    .legend-box { position: absolute; bottom: 15px; left: 15px; background: rgba(0,0,0,0.6); padding: 12px; border-radius: 6px; border: 1px solid #333; font-size: 11px; }
                    .lg-item { display: flex; align-items: center; margin-bottom: 4px; }
                    .lg-color { width: 11px; height: 11px; border-radius: 50%; margin-right: 6px; }
                </style>
                <script src="https://d3js.org/d3.v6.min.js"></script>
            </head>
            <body>
                <div id="canvas-container">
                    <div class="tax-tooltip" id="tt"></div>
                    <div class="legend-box">
                        <strong style="display:block; margin-bottom:5px;">Taxpayer Legend</strong>
                        <div class="lg-item"><div class="lg-color" style="background:#0284c7;"></div>Corporate (Badan)</div>
                        <div class="lg-item"><div class="lg-color" style="background:#f59e0b;"></div>Individual (OP)</div>
                        <div class="lg-item"><div class="lg-color" style="background:#ef4444;"></div>Offshore (LN)</div>
                        <div class="lg-item"><div class="lg-color" style="background:#64748b;"></div>No Reg (Non NPWP)</div>
                    </div>
                </div>
                <script>
                    // Safely load injected payload via text parsing
                    const graphData = %s;
                    
                    const box = d3.select("#canvas-container");
                    const w = box.node().clientWidth || 900;
                    const h = 620;
                    
                    const svg = box.append("svg").attr("width", w).attr("height", h);
                    const baseGroup = svg.append("g");
                    
                    svg.call(d3.zoom().scaleExtent([0.1, 5]).on("zoom", (e) => {
                        baseGroup.attr("transform", e.transform);
                    }));
                    
                    baseGroup.append("defs").append("marker")
                        .attr("id", "arrow")
                        .attr("viewBox", "0 -5 10 10")
                        .attr("refX", 20)
                        .attr("refY", 0)
                        .attr("markerWidth", 5)
                        .attr("markerHeight", 5)
                        .attr("orient", "auto")
                        .append("path").attr("d", "M0,-5L10,0L0,5").attr("class", "arrow-tip");
                        
                    const cmap = { "Badan": "#0284c7", "OP": "#f59e0b", "LN": "#ef4444", "Non NPWP": "#64748b" };
                    
                    const sim = d3.forceSimulation(graphData.nodes)
                        .force("link", d3.forceLink(graphData.links).id(d => d.id).distance(100))
                        .force("charge", d3.forceManyBody().strength(-180))
                        .force("center", d3.forceCenter(w/2, h/2))
                        .force("collide", d3.forceCollide().radius(d => d.size + 5));
                        
                    const link = baseGroup.append("g").selectAll("line")
                        .data(graphData.links).enter().append("line")
                        .attr("class", "edge-line").attr("marker-end", "url(#arrow)");
                        
                    const node = baseGroup.append("g").selectAll("circle")
                        .data(graphData.nodes).enter().append("circle")
                        .attr("class", "node-circle")
                        .attr("r", d => d.size)
                        .attr("fill", d => cmap[d.type] || "#10b981")
                        .call(d3.drag().on("start", ds).on("drag", dg).on("end", de));
                        
                    const lbl = baseGroup.append("g").selectAll("text")
                        .data(graphData.nodes.filter(d => d.size > 10)).enter().append("text")
                        .attr("class", "node-text").text(d => d.name.substring(0,14));
                        
                    const tooltip = d3.select("#tt");
                    
                    node.on("mouseover", function(e, d) {
                        tooltip.style("display", "block").html(`
                            <b>Taxpayer ID:</b> ${d.id}<br/>
                            <b>Name:</b> ${d.name}<br/>
                            <b>Type:</b> ${d.type}<br/>
                            <b>Centrality Score:</b> ${d.score}
                        `);
                        d3.select(this).style("stroke-width", "3px");
                    })
                    .on("mousemove", function(e) {
                        tooltip.style("left", (e.pageX + 15) + "px").style("top", (e.pageY - 25) + "px");
                    })
                    .on("mouseout", function() {
                        tooltip.style("display", "none");
                        d3.select(this).style("stroke-width", "1.5px");
                    });
                    
                    sim.on("tick", () => {
                        link.attr("x1", d => d.source.x).attr("y1", d => d.source.y)
                            .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
                        node.attr("cx", d => d.x).attr("cy", d => d.y);
                        lbl.attr("x", d => d.x + d.size + 2).attr("y", d => d.y + 3);
                    });
                    
                    function ds(e, d) { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; }
                    function dg(e, d) { d.fx = e.x; d.fy = e.y; }
                    function de(e, d) { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }
                </script>
            </body>
            </html>
            """ % d3_json_string
            
            # Safe rendering inside Streamlit components context
            components.html(html_code, height=640, scrolling=False)

    # ==================== TAB 3: MATRIX LEADERBOARDS ====================
    with tab3:
        st.subheader("📊 Network Centrality Metrics Rankings Leaderboard")
        st.markdown("Use this ranking spreadsheet matrix to identify corporate actors based on their absolute structural graph scores.")
        
        if len(G) == 0:
            st.info("The network is currently empty based on your sidebar filter parameters.")
        else:
            rank_records = []
            for n_id, attrs in G.nodes(data=True):
                rank_records.append({
                    "Taxpayer ID": n_id,
                    "Taxpayer Name": attrs.get('name', 'Unknown'),
                    "Taxpayer Category": attrs.get('type', 'Unknown'),
                    "Out-Degree (Holding Multiplier)": out_degree.get(n_id, 0),
                    "In-Degree (Investment Load)": in_degree.get(n_id, 0),
                    "Betweenness (Structural Bridge Score)": betweenness.get(n_id, 0)
                })
                
            rank_df = pd.DataFrame(rank_records)
            
            sort_metric = st.selectbox("Sort Dataset Hierarchy By:", [
                "Out-Degree (Holding Multiplier)", 
                "In-Degree (Investment Load)", 
                "Betweenness (Structural Bridge Score)"
            ])
            
            display_df = rank_df.sort_values(by=sort_metric, ascending=False).reset_index(drop=True)
            
            # Format and show dataframe with custom visualization gradients
            st.dataframe(display_df.style.background_gradient(subset=[sort_metric], cmap="Blues"), use_container_width=True)
            
            # CSV Download Action
            csv_blob = display_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export Full Centrality Analysis to CSV",
                data=csv_blob,
                file_name="tax_network_centrality_output.csv",
                mime="text/csv"
            )

    # ==================== TAB 4: LINEAGE EXPLORER ====================
    with tab4:
        st.subheader("🔍 Target Taxpayer 360° Lineage Tree Explorer")
        st.markdown("Isolate any tax entity from the dictionary drop-down to map out their instant upstream investors and downstream operational holdings.")
        
        # Build selection array using matching index keys
        picker_options = [f"{row['nama']} ({row['id']})" for _, row in final_nodes_df.iterrows()]
        
        if not picker_options:
            st.info("No active taxpayers available to look up under current filter conditions.")
        else:
            selected_picker = st.selectbox("Search/Select Target Taxpayer Entity:", options=picker_options)
            
            if selected_picker:
                # Isolate target string key extraction
                picked_id = selected_picker.split("(")[-1].replace(")", "").strip()
                node_profile = final_nodes_df[final_nodes_df['id'] == picked_id].iloc[0]
                
                st.markdown(f"""
                <div style='background-color:#1e293b; padding:15px; border-radius:8px; border-left:5px solid #0ea5e9; margin-bottom:20px;'>
                    <b>Selected Entity Profile:</b><br/>
                    • 🏢 <b>Name:</b> {node_profile['nama']}<br/>
                    • 💳 <b>Taxpayer Masked ID:</b> {node_profile['id']}<br/>
                    • 🏷️ <b>Category Grouping:</b> {node_profile['jenis_node']}
                </div>
                """, unsafe_allow_html=True)
                
                # Compute upstream parental tracking arrays
                investors_list = []
                if G.has_node(picked_id):
                    for parent in G.predecessors(picked_id):
                        edge_attrs = G.get_edge_data(parent, picked_id)
                        investors_list.append({
                            "Investor ID": parent,
                            "Investor Corporate Name": G.nodes[parent].get('name', 'Unknown'),
                            "Taxpayer Class": G.nodes[parent].get('type', 'Unknown'),
                            "Equity Stake (%)": f"{edge_attrs.get('percentage', 0)} %",
                            "Capital Injected Value": f"Rp {edge_attrs.get('weight', 0):,.2f}",
                            "Dividends Routed": f"Rp {edge_attrs.get('dividend', 0):,.2f}"
                        })
                        
                # Compute downstream operational holding structures
                subsidiaries_list = []
                if G.has_node(picked_id):
                    for child in G.successors(picked_id):
                        edge_attrs = G.get_edge_data(picked_id, child)
                        subsidiaries_list.append({
                            "Subsidiary ID": child,
                            "Subsidiary Name": G.nodes[child].get('name', 'Unknown'),
                            "Taxpayer Class": G.nodes[child].get('type', 'Unknown'),
                            "Ownership Share (%)": f"{edge_attrs.get('percentage', 0)} %",
                            "Equity Book Value": f"Rp {edge_attrs.get('weight', 0):,.2f}",
                            "Dividends Earned": f"Rp {edge_attrs.get('dividend', 0):,.2f}"
                        })
                        
                layout_col1, layout_col2 = st.columns(2)
                
                with layout_col1:
                    st.markdown("🔺 **Immediate Parent Shareholders & Capital Origins:**")
                    if investors_list:
                        st.dataframe(pd.DataFrame(investors_list), use_container_width=True)
                    else:
                        st.info("No upstream parent corporate entities found. (Taxpayer is a group Apex or Ultimate Owner).")
                        
                with layout_col2:
                    st.markdown("🔻 **Downstream Investment Portfolio & Subsidiaries:**")
                    if subsidiaries_list:
                        st.dataframe(pd.DataFrame(subsidiaries_list), use_container_width=True)
                    else:
                        st.info("No downstream subsidiaries found. (Taxpayer is an Operational Endpoint Company).")
else:
    st.warning("Ecosystem data pipeline disabled. Please place nodes_masked.csv and edges_masked_part1_a.csv inside the app workspace root.")
