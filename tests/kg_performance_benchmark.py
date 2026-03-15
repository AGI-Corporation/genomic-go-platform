import time
import asyncio
import numpy as np
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from research_framework.knowledge_graph import BiologicalKnowledgeGraph

async def benchmark_predict_links():
    kg = BiologicalKnowledgeGraph(api_key="dummy")

    # Generate 2000 nodes with random embeddings
    num_nodes = 2000
    embedding_dim = 1024

    print(f"Adding {num_nodes} nodes to the graph...")
    for i in range(num_nodes):
        node_id = f"node_{i}"
        embedding = np.random.rand(embedding_dim).astype(np.float32)
        kg.graph.add_node(node_id, embedding=embedding)

    print("Starting predict_links benchmark...")
    start_time = time.time()
    predictions = kg.predict_links(threshold=0.99)
    end_time = time.time()

    total_time = end_time - start_time
    print(f"Completed link prediction for {num_nodes} nodes in {total_time:.4f} seconds")
    print(f"Found {len(predictions)} potential links")
    return total_time

if __name__ == "__main__":
    asyncio.run(benchmark_predict_links())
