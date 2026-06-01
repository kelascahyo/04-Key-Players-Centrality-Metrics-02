import streamlit as st
import pandas as pd
import networkx as nx
import json
import streamlit.components.v1 as components

# Set page configuration for professional data platform layout
st.set_page_config(
    page_title="Tax Corporate Network & Centrality Analysis Platform",
    page_icon="🕸️",
    layout="wide"
)

# Main Dashboard Title & Subtitle
st.title("🕸️ Tax Corporate Network & Centrality Analysis Platform")
st.caption("An interactive network analytics tool designed for tax investigators, compliance auditors, and beginners to uncover ultimate beneficial owners, holding company patterns, and corporate group influence.")

# --- SIDEBAR CONTROL PANEL ---
st.sidebar.header("📁 Data & Configuration Panel")

# Cached function to safely load datasets
@st.cache_data
def load_data():
    try:
        nodes = pd.read_csv("nodes_masked.csv")
        edges = pd.read_csv("edges_masked_part1_a.csv")
        return nodes, edges
    except Exception as e:
        st.error(f"Error loading files: {e}. Please ensure 'nodes_masked.csv' and 'edges_masked_part1_a.csv' are in the same directory as this script.")
        return None, None

nodes_df, edges_df = load_data()

if nodes_df is not None and edges_df is not None:
    # Sidebar Filtering Options
    st.sidebar.subheader("🔍 Subgraph Filtering Tools")
    
    # Filter out relationships below a certain ownership threshold
    min_share = st.sidebar.slider(
        "Minimum Ownership Percentage (%)", 
        min_value=0.0, 
        max_value=100.0, 
        value=0.0, 
        step=0.5,
        help="Filter out weak equity linkages. Setting this higher helps simplify the network matrix."
    )
    
    # Process graph based on threshold
    filtered_edges = edges_df[edges_df['persentase'] >= min_share]
    
    # Build NetworkX Directed Graph (DiGraph)
    G = nx.DiGraph()
    
    # Inject nodes with their tax attributes
    for _, row in nodes_df.iterrows():
        G.add_node(row['id'], name=row['nama'], type=row['jenis_node'])
        
    # Inject edges with transactional/equity attributes
    for _, row in filtered_edges.iterrows():
        if G.has_node(row['sumber']) and G.has_node(row['target']):
            G.add_edge(row['sumber'], row['target'], 
                       weight=float(row['nilai']), 
                       percentage=float(row['persentase']),
                       dividend=float(row['dividen']))
            
    # Clean up isolated nodes option for cleaner topology visual
    remove_isolated = st.sidebar.checkbox("Hide Unconnected Taxpayers (Isolated Nodes)", value=True)
    if remove_isolated:
        isolated = list(nx.isolates(G))
        G.remove_nodes_from(isolated)
        
    # --- CALCULATE GRAPH CENTRALITY METRICS VIA NETWORKX ---
    out_degree = nx.out_degree_centrality(G)
    in_degree = nx.in_degree_centrality(G)
    
    # Performance check: Use sampled approximation for betweenness if graph size is massive
    if len(G) > 2000:
        betweenness = nx.betweenness_centrality(G, k=min(200, len(G)))
    else:
        betweenness = nx.betweenness_centrality(G)
        
    # Bind calculations back as node graph attributes
    for node in G.nodes():
        G.nodes[node]['out_degree'] = out_degree.get(node, 0)
        G.nodes[node]['in_degree'] = in_degree.get(node, 0)
        G.nodes[node]['betweenness'] = betweenness.get(node, 0)

    # --- MAIN PLATFORM TABS ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "📖 Educational Guide & Dashboard Overview", 
        "🕸️ Interactive D3.js Network Visualization", 
        "📊 Centrality Metrics & Key Players Rank", 
        "🔍 Individual Taxpayer Search & Lineage"
    ])
    
    # ==================== TAB 1: EDUCATIONAL GUIDE (English) ====================
    with tab1:
        st.markdown("""
## 📘 Educational Guide: Network Analytics in Corporate Taxation

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
    * *Tax Auditing Significance:* A high Betweenness score flags **Conduit Companies, Intermediary Holding Structures, or Middlemen**. If dividends or equity funds pass from an operational subsidiary up to an offshore parent entity across different sub-groups, they often route through these specific bridge nodes. In tax risk mapping, these structures are high-priority targets for studying dividend routing and treaty shopping.

---
### 📈 Live Network Overview
""")
        # Key Metric Cards
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Active Taxpayers in View", f"{len(G):,}")
        col2.metric("Total Equity Linkages", f"{G.number_of_edges():,}")
        col3.metric("Avg Ownership Links per Node", f"{G.number_of_edges()/len(G) if len(G)>0 else 0:.2f}")
        
        # Identify the apex node based on out-degree
        max_out_node = max(out_degree, key=out_degree.get) if out_degree else "N/A"
        max_out_name = G.nodes[max_out_node]['name'] if max_out_node in G else "N/A"
        col4.metric("Top Group Apex Entity", f"ID: {max_out_node}", help=f"Taxpayer Name: {max_out_name}")
        
        st.markdown("""
### 🚀 Step-by-Step Navigation Guide:
1. Move to **Tab 2 (Interactive D3.js Network Visualization)** to visually explore structural clusters, locate prominent actors, and view dynamic circle scaling based on calculated influence scores.
2. Move to **Tab 3 (Centrality Metrics & Key Players Rank)** to inspect a clean, tabular leaderboard of taxpayers sorted by risk/influence scores. Data can be exported as a raw spreadsheet.
3. Move to **Tab 4 (Individual Taxpayer Search & Lineage)** to isolate a specific tycoon or subsidiary and drill down into their immediate parent owners and investment portfolio.
""")

    # ==================== TAB 2: D3.JS INTERACTIVE VISUALIZATION ====================
    with tab2:
        st.subheader("🕸️ Dynamic Network Topology Map (D3.js Rendering Engine)")
        st.markdown("""
*Instructions:* Use your mouse scrollwheel to **zoom in/out** and click-and-drag empty spaces to **pan** across the digital map. 
**Hover** your mouse pointer over any colored circle to view registration details and centrality scores. **Drag** circles around to restructure the physics layout in real-time.
""")
        
        # Selection option to alter dynamic node sizing metric
        size_metric = st.selectbox(
            "Select Centrality Metric to Drive Dynamic Node Sizing:",
            ["Out-Degree Centrality (Holding/Investor Influence)", 
             "In-Degree Centrality (Capital Injection Load)", 
             "Betweenness Centrality (Structural Bridge Indicator)"]
        )
        
        metric_key = "out_degree"
        if "In-Degree" in size_metric:
            metric_key = "in_degree"
        elif "Betweenness" in size_metric:
            metric_key = "betweenness"
            
        # User constraint to handle UI responsiveness 
        max_d3_nodes = st.slider("Limit visualization to Top N most central nodes for smooth UI performance:", 50, 1000, 250)
        
        # Isolate top entities by selected metric for visualization pipeline
        sorted_nodes = sorted(G.nodes(data=True), key=lambda x: x[1].get(metric_key, 0), reverse=True)[:max_d3_nodes]
        subgraph_nodes = [n[0] for n in sorted_nodes]
        H = G.subgraph(subgraph_nodes)
        
        # Construct optimized JSON object payload for the D3 frontend script
        d3_nodes = []
        for node_id, attrs in H.nodes(data=True):
            val = attrs.get(metric_key, 0)
            # Re-scale node size mapping based on chosen metric properties
            size_val = 5 + (val * 80) if metric_key != "betweenness" else 5 + (val * 250)
            
            d3_nodes.append({
                "id": str(node_id),
                "name": str(attrs.get('name', 'Unknown')),
                "type": str(attrs.get('type', 'Badan')),
                "metric_val": round(float(val), 5),
                "size": float(size_val)
            })
            
        d3_links = []
        for u, v, attrs in H.edges(data=True):
            d3_links.append({
                "source": str(u),
                "target": str(v),
                "percentage": float(attrs.get('percentage', 0)),
                "value": float(attrs.get('weight', 0)),
                "dividend": float(attrs.get('dividend', 0))
            })
            
        d3_data = {"nodes": d3_nodes, "links": d3_links}
        d3_json_str = json.dumps(d3_data)
        
        # HTML template without using f-string or % placeholders to avoid JavaScript/CSS curly brace compilation conflicts
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {
                    margin: 0;
                    padding: 0;
                    background-color: #1e1e24;
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    overflow: hidden;
                    color: #ffffff;
                }
                #network-container {
                    width: 100%;
                    height: 650px;
                    position: relative;
                }
                .node {
                    stroke: #ffffff;
                    stroke-width: 1.5px;
                    cursor: pointer;
                }
                .link {
                    stroke: #7f8c8d;
                    stroke-opacity: 0.4;
                    stroke-width: 1.5px;
                    fill: none;
                }
                .link-arrow {
                    fill: #7f8c8d;
                    opacity: 0.5;
                }
                .text {
                    font-size: 10px;
                    fill: #ecf0f1;
                    pointer-events: none;
                    text-shadow: 0px 1px 2px #000000;
                }
                .tooltip {
                    position: absolute;
                    background: rgba(27, 38, 59, 0.95);
                    border: 1px solid #00b4d8;
                    border-radius: 6px;
                    padding: 12px;
                    font-size: 12px;
                    color: #ffffff;
                    pointer-events: none;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
                    line-height: 1.5em;
                    display: none;
                    z-index: 1000;
                }
                .legend {
                    position: absolute;
                    bottom: 20px;
                    left: 20px;
                    background: rgba(0, 0, 0, 0.7);
                    padding: 15px;
                    border-radius: 8px;
                    border: 1px solid #444444;
                    font-size: 11px;
                }
                .legend-item {
                    display: flex;
                    align-items: center;
                    margin-bottom: 5px;
                }
                .legend-color {
                    width: 12px;
                    height: 12px;
                    border-radius: 50%;
                    margin-right: 8px;
                }
            </style>
            <script src="https://d3js.org/d3.v6.min.js"></script>
        </head>
        <body>
            <div id="network-container">
                <div class="tooltip" id="tooltip"></div>
                <div class="legend">
                    <strong style="font-size:12px; display:block; margin-bottom:8px;">Taxpayer Types Legend</strong>
                    <div class="legend-item"><div class="legend-color" style="background:#00b4d8;"></div>Badan (Corporate)</div>
                    <div class="legend-item"><div class="legend-color" style="background:#ffb703;"></div>OP (Individual Tycoon)</div>
                    <div class="legend-item"><div class="legend-color" style="background:#e63946;"></div>LN (Offshore/Foreign Entity)</div>
                    <div class="legend-item"><div class="legend-color" style="background:#8d99ae;"></div>Non NPWP (No Tax Registration)</div>
                </div>
            </div>

            <script>
                // TARGET_DATA_PLACEHOLDER will be replaced cleanly by Python .replace()
                const data = TARGET_DATA_PLACEHOLDER;
                const container = d3.select("#network-container");
                const width = container.node().clientWidth || 1000;
                const height = 650;

                const svg = container.append("svg")
                    .attr("width", width)
                    .attr("height", height)
                    .call(d3.zoom().on("zoom", function (event) {
                        g.attr("transform", event.transform);
                    }))
                    .append("g");

                // Config arrow tips for link directions
                svg.append("defs").selectAll("marker")
                    .data(["end"])
                    .enter().append("marker")
                    .attr("id", d => d)
                    .attr("viewBox", "0 -5 10 10")
                    .attr("refX", 22) 
                    .attr("refY", 0)
                    .attr("markerWidth", 6)
                    .attr("markerHeight", 6)
                    .attr("orient", "auto")
                    .append("path")
                    .attr("d", "M0,-5L10,0L0,5")
                    .attr("class", "link-arrow");

                const g = svg.append("g");

                // Mapping Hex Colors to Taxpayer Type strings
                const colorMap = {
                    "Badan": "#00b4d8",
                    "OP": "#ffb703",
                    "LN": "#e63946",
                    "Non NPWP": "#8d99ae"
                };

                const getColor = d => colorMap[d.type] || "#a8dadc";

                // Setup simulation properties
                const simulation = d3.forceSimulation(data.nodes)
                    .force("link", d3.forceLink(data.links).id(d => d.id).distance(120))
                    .force("charge", d3.forceManyBody().strength(-220))
                    .force("center", d3.forceCenter(width / 2, height / 2))
                    .force("collision", d3.forceCollide().radius(d => d.size + 6));

                // Bind linkages
                const link = g.append("g")
                    .attr("class", "links")
                    .selectAll("line")
                    .data(data.links)
                    .enter().append("line")
                    .attr("class", "link")
                    .attr("marker-end", "url(#end)");

                // Bind nodes
                const node = g.append("g")
                    .attr("class", "nodes")
                    .selectAll("circle")
                    .data(data.nodes)
                    .enter().append("circle")
                    .attr("class", "node")
                    .attr("r", d => d.size)
                    .attr("fill", getColor)
                    .call(d3.drag()
                        .on("start", dragstarted)
                        .on("drag", dragged)
                        .on("end", dragended));

                // Conditional node labels text based on sizing importance
                const label = g.append("g")
                    .attr("class", "labels")
                    .selectAll("text")
                    .data(data.nodes.filter(d => d.size > 12))
                    .enter().append("text")
                    .attr("class", "text")
                    .text(d => d.name.substring(0, 16));

                const tooltip = d3.select("#tooltip");

                // Hover triggers
                node.on("mouseover", function(event, d) {
                    tooltip.style("display", "block")
                        .html("<strong>Taxpayer ID:</strong> " + d.id + "<br/>" +
                              "<strong>Name:</strong> " + d.name + "<br/>" +
                              "<strong>Type:</strong> " + d.type + "<br/>" +
                              "<strong>Centrality Score:</strong> " + d.metric_val);
                    d3.select(this).style("stroke", "#ffffff").style("stroke-width", "3px");
                })
                .on("mousemove", function(event) {
                    tooltip.style("left", (event.pageX + 15) + "px")
                           .style("top", (event.pageY - 20) + "px");
                })
                .on("mouseout", function() {
                    tooltip.style("display", "none");
                    d3.select(this).style("stroke", "#ffffff").style("stroke-width", "1.5px");
                });

                simulation.on("tick", () => {
                    link
                        .attr("x1", d => d.source.x)
                        .attr("y1", d => d.source.y)
                        .attr("x2", d => d.target.x)
                        .attr("y2", d => d.target.y);

                    node
                        .attr("cx", d => d.x)
                        .attr("cy", d => d.y);

                    label
                        .attr("x", d => d.x + d.size + 2)
                        .attr("y", d => d.y + 4);
                });

                function dragstarted(event, d) {
                    if (!event.active) simulation.alphaTarget(0.3).restart();
                    d.fx = d.x;
                    d.fy = d.y;
                }

                function dragged(event, d) {
                    d.fx = event.x;
                    d.fy = event.y;
                }

                function dragended(event, d) {
                    if (!event.active) simulation.alphaTarget(0);
                    d.fx = null;
                    d.fy = null;
                }
            </script>
        </body>
        </html>
        """
        
        # Safely inject the JSON string without triggering % formatting operators or f-string exceptions
        final_html_code = html_template.replace("TARGET_DATA_PLACEHOLDER", d3_json_str)
        
        # Execute HTML component injector
        components.html(final_html_code, height=670, scrolling=False)

    # ==================== TAB 3: QUANTITATIVE RANKINGS ====================
    with tab3:
        st.subheader("📊 Network Centrality Rankings Leaderboard")
        st.markdown("""
Review the quantitative scores computed across all nodes. 
This data matrix serves as an audit pipeline to isolate key risk entities, conglomerate heads, or conduit companies.
""")
        
        # Build tabular compilation from network metrics
        metrics_records = []
        for node_id, attrs in G.nodes(data=True):
            metrics_records.append({
                "Taxpayer ID": node_id,
                "Taxpayer Name": attrs.get('name', 'Unknown'),
                "Taxpayer Type": attrs.get('type', 'Unknown'),
                "Out-Degree (Holding Score)": out_degree.get(node_id, 0),
                "In-Degree (Investment Load)": in_degree.get(node_id, 0),
                "Betweenness (Bridge Index)": betweenness.get(node_id, 0)
            })
            
        metrics_df = pd.DataFrame(metrics_records)
        
        # Table Sort Control Widget
        sort_by = st.selectbox("Sort Data Table Hierarchy By:", [
            "Out-Degree (Holding Score)", 
            "In-Degree (Investment Load)", 
            "Betweenness (Bridge Index)"
        ])
        
        sorted_df = metrics_df.sort_values(by=sort_by, ascending=False).reset_index(drop=True)
        
        # FIX: Terhindar dari ImportError matplotlib dengan menggunakan representasi tabel standar yang aman dan berkinerja tinggi
        st.dataframe(sorted_df, use_container_width=True)
        
        # Export functionality
        csv_data = sorted_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Full Network Centrality Report (CSV)",
            data=csv_data,
            file_name="tax_network_centrality_report.csv",
            mime="text/csv"
        )

    # ==================== TAB 4: INDIVIDUAL TAXPAYER EXPLORER ====================
    with tab4:
        st.subheader("🔍 Target Taxpayer 360° Lineage Explorer")
        st.markdown("Search for any individual tycoon or corporation to immediately trace their parent shareholders and downstream corporate investment portfolios.")
        
        # Structured Search bar options text format
        search_options = [f"{row['nama']} ({row['id']})" for _, row in nodes_df.iterrows()]
        selected_search = st.selectbox("Type to Search Taxpayer Name or Masked ID:", search_options)
        
        if selected_search:
            # Safely extract the raw int ID out of parenthesis formatting
            target_id = int(selected_search.split("(")[-1].replace(")", ""))
            target_node_attrs = nodes_df[nodes_df['id'] == target_id].iloc[0]
            
            st.markdown(f"""
#### 💳 Profile Details:
* **Taxpayer Corporate Name:** {target_node_attrs['nama']}
* **Taxpayer Masked ID:** {target_node_attrs['id']}
* **Taxpayer Registered Entity Class:** {target_node_attrs['jenis_node']}
""")
            
            # Fetch immediate predecessors (Who owns shares in this node)
            owners = []
            if G.has_node(target_id):
                for p in G.predecessors(target_id):
                    edge_data = G.get_edge_data(p, target_id)
                    owners.append({
                        "Investor ID": p,
                        "Investor Name": G.nodes[p]['name'],
                        "Investor Type": G.nodes[p]['type'],
                        "Ownership Share (%)": edge_data.get('percentage'),
                        "Equity Value (IDR)": f"Rp {edge_data.get('weight', 0):,}",
                        "Dividends Paid Up (IDR)": f"Rp {edge_data.get('dividend', 0):,}"
                    })
                    
            # Fetch immediate successors (What entities does this node own shares in)
            subsidiaries = []
            if G.has_node(target_id):
                for s in G.successors(target_id):
                    edge_data = G.get_edge_data(target_id, s)
                    subsidiaries.append({
                        "Subsidiary ID": s,
                        "Subsidiary Name": G.nodes[s]['name'],
                        "Subsidiary Type": G.nodes[s]['type'],
                        "Ownership Share (%)": edge_data.get('percentage'),
                        "Equity Value (IDR)": f"Rp {edge_data.get('weight', 0):,}",
                        "Dividends Received (IDR)": f"Rp {edge_data.get('dividend', 0):,}"
                    })
            
            col_own, col_sub = st.columns(2)
            
            with col_own:
                st.markdown("🔺 **Immediate Parent Shareholders (Who controls this entity?):**")
                if owners:
                    st.dataframe(pd.DataFrame(owners), use_container_width=True)
                else:
                    st.info("No corporate parents found in this dataset (This node may act as an Ultimate Holding Company).")
                    
            with col_sub:
                st.markdown("🔻 **Immediate Corporate Investments (What companies does this entity own?):**")
                if subsidiaries:
                    st.dataframe(pd.DataFrame(subsidiaries), use_container_width=True)
                else:
                    st.info("No corporate subsidiaries found in this dataset (This entity is an Operational Endpoint Company).")

else:
    st.warning("Data loading suspended. Please verify data assets are correctly positioned.")
