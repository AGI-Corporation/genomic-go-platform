import streamlit as st
import asyncio
import os
import json
from src.research_framework.discovery_tool import GenomicDiscoveryTool
from src.schemas.genomic_entities import ResearchDiscovery

st.set_page_config(
    page_title="Genomic.go Swarm Workbench", page_icon="🧬", layout="wide"
)

st.title("🧬 Genomic.go: Swarm Intelligence Workbench")
st.markdown("### Accelerating Genomic Discovery with Mistral AI")

if "MISTRAL_API_KEY" not in os.environ:
    st.error(
        "MISTRAL_API_KEY not found in environment. Please set it to use the workbench."
    )
    st.stop()

# Initialize tool in session state
if "tool" not in st.session_state:
    st.session_state.tool = GenomicDiscoveryTool()

tool = st.session_state.tool

# Sidebar for Swarm Status
st.sidebar.header("🐝 Swarm Status")
agents = list(tool.swarm.orchestrator.agents.keys())
st.sidebar.write(f"Active Agents: {len(agents)}")
for agent in agents:
    st.sidebar.markdown(f"- {agent}")

st.sidebar.divider()
st.sidebar.info("Built for Mistral Worldwide Hackathon 2025")

# Main Interface
indication = st.text_input(
    "Enter Target Indication (e.g., Alzheimer's, Cystic Fibrosis):",
    placeholder="Type disease here...",
)

# Data Integration Section
with st.expander("📂 Clinical & Genomic Data Integration"):
    st.info("Select or upload biological datasets to enhance the research swarm's context.")
    col_data1, col_data2 = st.columns(2)
    with col_data1:
        vcf_file = st.selectbox("Select Patient VCF (Genomic Variants):",
                               ["None", "data/sample/patient_001.vcf"])
    with col_data2:
        fasta_file = st.selectbox("Select Target FASTA (Protein Sequence):",
                                 ["None", "data/sample/target_sequence.fasta"])

    image_file = st.file_uploader("Upload Biological Image (Protein Structure/Gel):", type=["png", "jpg", "jpeg"])
    if not image_file:
        st.caption("Or use sample image:")
        if st.checkbox("Use sample protein structure"):
            image_path = "data/sample/protein_structure.png"
        else:
            image_path = None
    else:
        # Save uploaded file
        os.makedirs("temp", exist_ok=True)
        image_path = os.path.join("temp", image_file.name)
        with open(image_path, "wb") as f:
            f.write(image_file.getbuffer())

if st.button("🚀 Accelerate Research"):
    if not indication:
        st.warning("Please enter an indication first.")
    else:
        with st.spinner(f"Deploying swarm for {indication}..."):
            # Execute Discovery
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                report = loop.run_until_complete(tool.accelerate_research(
                    indication,
                    vcf_path=vcf_file if vcf_file != "None" else None,
                    fasta_path=fasta_file if fasta_file != "None" else None,
                    image_path=image_path
                ))

                # Success Display
                st.success(f"Research pipeline completed for {indication}!")

                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("📋 Discovery Report")
                    st.write(f"**Indication:** {report['indication']}")
                    st.write(f"**Knowledge Graph Nodes:** {report['kg_nodes']}")

                    # Display expanded swarm results in tabs
                    tab1, tab2, tab3, tab4 = st.tabs(["Swarm Summary", "Bioinformatics", "Safety & Regulatory", "Multimodal Analysis"])
                    with tab1:
                        st.json(report["swarm_intelligence_summary"][:3])
                    with tab2:
                        st.json(report["swarm_intelligence_summary"][3:4])
                    with tab3:
                        st.json(report["swarm_intelligence_summary"][4:6])
                    with tab4:
                        st.json(report["swarm_intelligence_summary"][6:])
                        if "patient_feasibility" in report:
                            st.write("**Patient Feasibility Matching:**")
                            st.json(report["patient_feasibility"])

                with col2:
                    st.subheader("⚖️ Mistral Evaluation")
                    eval_data = report["evaluation"]
                    for criterion, details in eval_data.items():
                        if isinstance(details, dict):
                            st.metric(
                                label=criterion.replace("_", " ").title(),
                                value=f"{details.get('score', 'N/A')}/3",
                            )
                            st.caption(details.get("explanation", ""))

                st.divider()
                st.subheader("🧪 Lab Notebook")
                notebook_path = f"lab_notebook/discovery_{indication.lower().replace(' ', '_')}.json"
                if os.path.exists(notebook_path):
                    with open(notebook_path, "r") as f:
                        st.download_button(
                            "Download Full Research JSON",
                            f,
                            file_name=os.path.basename(notebook_path),
                        )

            except Exception as e:
                st.error(f"Error during discovery: {str(e)}")
            finally:
                loop.close()

# Knowledge Graph Section
st.divider()
st.subheader("🕸️ Biological Knowledge Graph")
st.write(
    f"The graph currently contains {len(tool.kg.graph.nodes)} high-fidelity entities linked by Mistral semantic embeddings."
)

if st.checkbox("Show Interactive Graph Visualization"):
    import plotly.graph_objects as go
    import networkx as nx

    G = tool.kg.graph
    if len(G.nodes) > 0:
        pos = nx.spring_layout(G)
        edge_x = []
        edge_y = []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=0.5, color='#888'),
            hoverinfo='none',
            mode='lines')

        node_x = []
        node_y = []
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)

        node_colors = []
        node_text = []
        color_map = {"disease": "#FF4B4B", "gene": "#1C83E1", "protein": "#00C0F2", "compound": "#29B09D"}

        for node, data in G.nodes(data=True):
            node_type = data.get("type", "unknown")
            node_colors.append(color_map.get(node_type, "#888"))

            metadata = data.get("metadata", {})
            desc = metadata.get("description", "No description available.")
            node_text.append(f"<b>ID:</b> {node}<br><b>Type:</b> {node_type}<br><b>Desc:</b> {desc}")

        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers',
            hoverinfo='text',
            text=node_text,
            marker=dict(
                color=node_colors,
                size=15,
                line_width=2))

        fig = go.Figure(data=[edge_trace, node_trace],
                     layout=go.Layout(
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=0,l=0,r=0,t=0),
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                    )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("The graph is currently empty. Run research discovery to populate nodes.")

if st.checkbox("Show Graph Raw Data"):
    st.write(list(tool.kg.graph.nodes(data=True)))

# Augmented Reality Integration
st.divider()
st.subheader("🕶️ DeSci AR Visualization")
st.info("Holographic protein structure rendering powered by DeSci Virtual Labs")

col_ar1, col_ar2 = st.columns([1, 2])
with col_ar1:
    molecule_id = st.text_input("Enter Molecule ID for AR:", value="BACE1_inhibitor_01")
    if st.button("Generate AR View"):
        from src.visualization.ar_adapter import ARAdapter
        ar = ARAdapter()
        config = ar.generate_holographic_config(molecule_id)
        st.success("AR Scene Generated!")
        st.json(config)

with col_ar2:
    st.image("https://placehold.co/600x400?text=AR+Holographic+Preview+Waiting", caption="Spatial Preview")
