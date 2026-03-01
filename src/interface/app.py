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

# Sidebar for Swarm Status
st.sidebar.header("🐝 Swarm Status")
tool = GenomicDiscoveryTool()
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

if st.button("🚀 Accelerate Research"):
    if not indication:
        st.warning("Please enter an indication first.")
    else:
        with st.spinner(f"Deploying swarm for {indication}..."):
            # Execute Discovery
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                report = loop.run_until_complete(tool.accelerate_research(indication))

                # Success Display
                st.success(f"Research pipeline completed for {indication}!")

                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("📋 Discovery Report")
                    st.write(f"**Indication:** {report['indication']}")
                    st.write(f"**Knowledge Graph Nodes:** {report['kg_nodes']}")

                    # Display expanded swarm results in tabs
                    tab1, tab2, tab3 = st.tabs(["Swarm Summary", "Bioinformatics", "Safety & Regulatory"])
                    with tab1:
                        st.json(report["swarm_intelligence_summary"][:3])
                    with tab2:
                        st.json(report["swarm_intelligence_summary"][3:4])
                    with tab3:
                        st.json(report["swarm_intelligence_summary"][4:])

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
if st.checkbox("Show Graph Nodes"):
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
