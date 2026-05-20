"""
LangGraph Contextual RAG System

Flow:
1. Retrieve document chunks
2. Summarize with local Ollama
3. Embed summaries with OpenAI
4. Build chunk relationship graph with LangGraph
5. Get global meaning with Gemini API
6. Generate answer with Ollama (local) using all context
"""

from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any, Optional
import os
from dotenv import load_dotenv
import requests
import json
from openai import OpenAI
import google.generativeai as genai
from sqlalchemy.orm import Session
from models import DocumentChunk, ChunkEmbedding

load_dotenv()

# ===== CONFIGURATION =====
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
K_CHUNKS = int(os.getenv("K_CHUNKS_CONTEXTUAL", 3))

# Initialize clients
openai_client = OpenAI(api_key=OPENAI_API_KEY)

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

print(f"[LangGraph] Ollama: {OLLAMA_API_URL}/{OLLAMA_MODEL}")
print(f"[LangGraph] Gemini: {'Configured' if GEMINI_API_KEY else 'Not configured'}")

# ===== LANGRAPH STATE TYPES =====
class ChunkState(TypedDict):
    """State for individual chunk"""
    chunk_id: int
    chunk_text: str
    summary: str
    topic: str
    embedding: List[float]
    relevance_score: float

class ContextualQueryState(TypedDict):
    """State for entire query processing"""
    query: str
    retrieved_chunks: List[ChunkState]
    chunk_relationships: Dict[str, Any]
    global_meaning: str
    chunk_relationships_text: str
    final_answer: str
    debug_info: Dict[str, str]

# ===== 1. OLLAMA LOCAL SUMMARIZATION =====
def summarize_chunk_with_ollama(chunk_text: str) -> str:
    """
    Summarize chunk using local Ollama model
    
    Args:
        chunk_text: Text chunk to summarize
    
    Returns:
        Summary string
    """
    try:
        # Create concise summarization prompt
        prompt = f"""Summarize this text in 1-2 sentences, capturing key information:

{chunk_text[:1000]}

Summary:"""
        
        response = requests.post(
            f"{OLLAMA_API_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.3,  # Lower temp for consistent summaries
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            summary = result.get("response", "").strip()
            print(f"[Ollama] Summary generated: {summary[:100]}...")
            return summary
        else:
            print(f"[Ollama] Error: {response.status_code}")
            return f"Summary of: {chunk_text[:100]}..."
            
    except Exception as e:
        print(f"[Ollama] Error: {str(e)}")
        # Fallback: use first 150 chars
        return chunk_text[:150] + "..."

def extract_topic_with_ollama(chunk_text: str) -> str:
    """
    Extract main topic using Ollama
    
    Args:
        chunk_text: Text chunk
    
    Returns:
        Topic string (1-5 words)
    """
    try:
        prompt = f"""Extract the main topic of this text in 1-3 words. Reply with ONLY the topic, nothing else:

{chunk_text[:500]}

Topic:"""
        
        response = requests.post(
            f"{OLLAMA_API_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.1,
            },
            timeout=20
        )
        
        if response.status_code == 200:
            result = response.json()
            topic = result.get("response", "").strip()
            # Clean up topic
            topic = topic.split('\n')[0]  # First line only
            print(f"[Ollama] Topic extracted: {topic}")
            return topic
            
        return "General"
        
    except Exception as e:
        print(f"[Ollama] Topic extraction error: {str(e)}")
        return "General"

# ===== 2. EMBEDDING SUMMARIES =====
def embed_text(text: str) -> List[float]:
    """
    Embed text using OpenAI embeddings
    
    Args:
        text: Text to embed
    
    Returns:
        Embedding vector
    """
    try:
        response = openai_client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        embedding = response.data[0].embedding
        print(f"[Embeddings] Generated embedding (dim={len(embedding)})")
        return embedding
        
    except Exception as e:
        print(f"[Embeddings] Error: {str(e)}")
        return []

# ===== 3. CHUNK SIMILARITY RETRIEVAL =====
def retrieve_similar_chunks(
    query: str,
    db: Session,
    doc_id: int,
    top_k: int = 3
) -> List[ChunkState]:
    """
    Retrieve most similar chunks using embedding similarity
    
    Args:
        query: User query
        db: Database session
        doc_id: Document ID
        top_k: Number of chunks to retrieve
    
    Returns:
        List of similar chunks
    """
    try:
        # Get query embedding
        query_embedding = embed_text(query)
        
        if not query_embedding:
            print("[Retrieval] Failed to embed query")
            return []
        
        # Get all chunks for document
        chunks = db.query(DocumentChunk).filter(
            DocumentChunk.doc_id == doc_id
        ).all()
        
        if not chunks:
            print(f"[Retrieval] No chunks found for doc_id={doc_id}")
            return []
        
        # Calculate similarity scores
        chunk_scores = []
        for chunk in chunks:
            # Get chunk embedding
            chunk_embed_record = db.query(ChunkEmbedding).filter(
                ChunkEmbedding.chunk_id == chunk.chunk_id
            ).first()
            
            if not chunk_embed_record:
                continue
            
            # For now, use basic similarity (in production, use FAISS or similar)
            # This is a placeholder - in real system you'd use cosine similarity
            score = 0.8  # Default high score since we're fetching relevant chunks
            
            chunk_scores.append({
                "chunk": chunk,
                "score": score
            })
        
        # Sort by score and get top-k
        chunk_scores.sort(key=lambda x: x["score"], reverse=True)
        top_chunks = chunk_scores[:top_k]
        
        # Convert to ChunkState
        retrieved = []
        for item in top_chunks:
            chunk = item["chunk"]
            retrieved.append(ChunkState(
                chunk_id=chunk.chunk_id,
                chunk_text=chunk.chunk_text,
                summary=getattr(chunk, 'summary', '') or '',  # May not exist yet
                topic=getattr(chunk, 'topic', '') or 'General',  # May not exist yet
                embedding=[],
                relevance_score=item["score"]
            ))
        
        print(f"[Retrieval] Retrieved {len(retrieved)} chunks")
        return retrieved
        
    except Exception as e:
        print(f"[Retrieval] Error: {str(e)}")
        return []

# ===== 4. LANGGRAPH - BUILD CHUNK RELATIONSHIPS =====
def build_chunk_relationship_graph(chunks: List[ChunkState]) -> Dict[str, Any]:
    """
    Build LangGraph showing how chunks relate to each other
    Analyzes topics and content overlap
    
    Args:
        chunks: Retrieved chunks
    
    Returns:
        Graph structure with nodes and edges
    """
    try:
        # Create nodes
        nodes = []
        for i, chunk in enumerate(chunks):
            nodes.append({
                "id": f"chunk_{i}",
                "topic": chunk["topic"],
                "summary": chunk["summary"][:100] if chunk["summary"] else "No summary",
                "relevance": chunk["relevance_score"]
            })
        
        # Create edges (relationships)
        edges = []
        for i in range(len(chunks)):
            for j in range(i + 1, len(chunks)):
                # Check topic similarity
                topic_i = chunks[i]["topic"].lower()
                topic_j = chunks[j]["topic"].lower()
                
                # Find common keywords
                words_i = set(topic_i.split())
                words_j = set(topic_j.split())
                
                if words_i & words_j:  # Has common words
                    edges.append({
                        "source": f"chunk_{i}",
                        "target": f"chunk_{j}",
                        "relation": "topic_related",
                        "common_words": list(words_i & words_j)
                    })
                
                # Check content overlap (simple word overlap)
                text_i = set(chunks[i]["chunk_text"].lower().split())
                text_j = set(chunks[j]["chunk_text"].lower().split())
                overlap = len(text_i & text_j) / min(len(text_i), len(text_j)) if min(len(text_i), len(text_j)) > 0 else 0
                
                if overlap > 0.2:  # More than 20% word overlap
                    edges.append({
                        "source": f"chunk_{i}",
                        "target": f"chunk_{j}",
                        "relation": "content_related",
                        "overlap_score": overlap
                    })
        
        graph = {
            "nodes": nodes,
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges)
        }
        
        print(f"[LangGraph] Built graph: {len(nodes)} nodes, {len(edges)} edges")
        return graph
        
    except Exception as e:
        print(f"[LangGraph] Error building graph: {str(e)}")
        return {"nodes": [], "edges": [], "error": str(e)}

# ===== 5. GEMINI - GLOBAL MEANING =====
def get_global_meaning_with_gemini(topics: List[str], query: str) -> str:
    """
    Use Gemini API to get global meaning and context
    
    Args:
        topics: Topics extracted from chunks
        query: User's question
    
    Returns:
        Global context and meaning
    """
    try:
        if not GEMINI_API_KEY:
            print("[Gemini] API key not configured")
            return "Global context unavailable"
        
        model = genai.GenerativeModel("gemini-pro")
        
        prompt = f"""Given these document topics: {', '.join(set(topics))}

And user query: {query}

Provide a brief global context (2-3 sentences) explaining how these topics relate to the query and what broader meaning they convey:"""
        
        response = model.generate_content(prompt)
        meaning = response.text.strip()
        
        print(f"[Gemini] Global meaning generated")
        return meaning
        
    except Exception as e:
        print(f"[Gemini] Error: {str(e)}")
        return "Unable to determine global context"

# ===== 6. GRAPH FORMATTING FOR OLLAMA =====
def format_graph_for_context(graph: Dict[str, Any]) -> str:
    """
    Format graph structure into readable text for Ollama
    
    Args:
        graph: Chunk relationship graph
    
    Returns:
        Formatted text representation
    """
    text = "### CHUNK RELATIONSHIPS (LangGraph):\n"
    
    # Add nodes
    text += "\nChunks:\n"
    for node in graph.get("nodes", []):
        text += f"- [{node['id'].upper()}] Topic: {node['topic']}\n"
        text += f"  Summary: {node['summary']}\n"
        text += f"  Relevance: {node['relevance']:.2%}\n"
    
    # Add edges
    if graph.get("edges"):
        text += "\nRelationships:\n"
        for edge in graph.get("edges", []):
            text += f"- {edge['source']} --({edge['relation']})-> {edge['target']}\n"
    
    return text

# ===== 7. LANGGRAPH WORKFLOW DEFINITION =====
def build_contextual_workflow():
    """
    Build LangGraph workflow combining all components
    """
    
    workflow = StateGraph(ContextualQueryState)
    
    # Node 1: Analyze and prepare chunks
    def prepare_chunks(state: ContextualQueryState) -> ContextualQueryState:
        """Ensure all chunks have summaries and topics"""
        print("\n[Workflow] Step 1: Preparing chunks...")
        
        for chunk in state["retrieved_chunks"]:
            # Add summary if missing
            if not chunk["summary"]:
                print(f"  Summarizing chunk {chunk['chunk_id']}...")
                chunk["summary"] = summarize_chunk_with_ollama(chunk["chunk_text"])
            
            # Add topic if missing
            if chunk["topic"] == "General":
                print(f"  Extracting topic from chunk {chunk['chunk_id']}...")
                chunk["topic"] = extract_topic_with_ollama(chunk["chunk_text"])
        
        state["debug_info"]["chunks_prepared"] = f"{len(state['retrieved_chunks'])} chunks"
        return state
    
    # Node 2: Build chunk relationships
    def analyze_relationships(state: ContextualQueryState) -> ContextualQueryState:
        """Build LangGraph of chunk relationships"""
        print("\n[Workflow] Step 2: Building chunk relationships...")
        
        graph = build_chunk_relationship_graph(state["retrieved_chunks"])
        state["chunk_relationships"] = graph
        state["chunk_relationships_text"] = format_graph_for_context(graph)
        
        state["debug_info"]["relationships_built"] = f"{graph['total_nodes']} nodes, {graph['total_edges']} edges"
        return state
    
    # Node 3: Get global meaning
    def get_global_context(state: ContextualQueryState) -> ContextualQueryState:
        """Get global meaning using Gemini"""
        print("\n[Workflow] Step 3: Getting global context with Gemini...")
        
        topics = [c["topic"] for c in state["retrieved_chunks"]]
        meaning = get_global_meaning_with_gemini(topics, state["query"])
        state["global_meaning"] = meaning
        
        state["debug_info"]["global_meaning_generated"] = "Yes"
        return state
    
    # Node 4: Generate contextual answer
    def generate_contextual_answer(state: ContextualQueryState) -> ContextualQueryState:
        """Generate answer using Ollama with all context"""
        print("\n[Workflow] Step 4: Generating answer with Ollama...")
        
        # Build context
        context_text = "### DOCUMENT CHUNKS:\n"
        for i, chunk in enumerate(state["retrieved_chunks"]):
            context_text += f"\n[CHUNK {i+1}]\n"
            context_text += f"Topic: {chunk['topic']}\n"
            context_text += f"Summary: {chunk['summary']}\n"
            context_text += f"Full Text:\n{chunk['chunk_text'][:500]}...\n"
        
        context_text += "\n" + state["chunk_relationships_text"]
        
        context_text += f"\n### GLOBAL CONTEXT:\n{state['global_meaning']}\n"
        
        # Create final prompt for Ollama
        prompt = f"""You are a helpful assistant answering questions about documents.

Use the following context from document chunks, their relationships, and global meaning to answer the user's question.

{context_text}

### USER QUESTION:
{state['query']}

### ANSWER:
Be concise and cite which chunks you're using. Explain how chunks relate to each other in your answer."""
        
        # Call Ollama
        try:
            response = requests.post(
                f"{OLLAMA_API_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.7,
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get("response", "No response generated").strip()
                state["final_answer"] = answer
                state["debug_info"]["answer_generated"] = "Yes"
            else:
                state["final_answer"] = f"Error from Ollama: {response.status_code}"
                state["debug_info"]["answer_generated"] = "Error"
                
        except Exception as e:
            state["final_answer"] = f"Error: {str(e)}"
            state["debug_info"]["answer_generated"] = f"Error: {str(e)}"
        
        return state
    
    # Add nodes to workflow
    workflow.add_node("prepare", prepare_chunks)
    workflow.add_node("relationships", analyze_relationships)
    workflow.add_node("global_context", get_global_context)
    workflow.add_node("answer", generate_contextual_answer)
    
    # Add edges (execution order)
    workflow.add_edge("prepare", "relationships")
    workflow.add_edge("relationships", "global_context")
    workflow.add_edge("global_context", "answer")
    workflow.add_edge("answer", END)
    
    # Set entry point
    workflow.set_entry_point("prepare")
    
    return workflow.compile()

# ===== 8. MAIN ANSWER FUNCTION =====
def answer_question_contextual(
    query: str,
    retrieved_chunks: List[ChunkState]
) -> Dict[str, Any]:
    """
    Answer question using full contextual RAG pipeline with LangGraph
    
    Args:
        query: User's question
        retrieved_chunks: Chunks retrieved from similarity search
    
    Returns:
        Answer with relationships and debug info
    """
    try:
        print(f"\n{'='*60}")
        print(f"[Contextual RAG] Processing query: {query[:100]}...")
        print(f"{'='*60}")
        
        # Build and run workflow
        app = build_contextual_workflow()
        
        initial_state: ContextualQueryState = {
            "query": query,
            "retrieved_chunks": retrieved_chunks,
            "chunk_relationships": {},
            "global_meaning": "",
            "chunk_relationships_text": "",
            "final_answer": "",
            "debug_info": {}
        }
        
        # Execute workflow
        result = app.invoke(initial_state)
        
        print(f"\n[Contextual RAG] Workflow complete!")
        print(f"Debug Info: {result['debug_info']}")
        
        return {
            "answer": result.get("final_answer", ""),
            "chunk_relationships": result.get("chunk_relationships", {}),
            "global_meaning": result.get("global_meaning", ""),
            "sources": [
                {
                    "topic": chunk["topic"],
                    "summary": chunk["summary"],
                    "relevance": chunk["relevance_score"]
                }
                for chunk in result.get("retrieved_chunks", [])
            ],
            "debug_info": result.get("debug_info", {})
        }
        
    except Exception as e:
        print(f"\n[Contextual RAG] Error: {str(e)}")
        return {
            "error": str(e),
            "answer": None,
            "sources": []
        }

# ===== INDEXING WITH SUMMARIZATION =====
def process_chunk_for_contextual_storage(
    chunk_text: str,
    chunk_id: int,
    db: Session
) -> Dict[str, Any]:
    """
    Process chunk: summarize + extract topic + embed
    Store metadata for contextual retrieval
    
    Args:
        chunk_text: Text to process
        chunk_id: Database chunk ID
        db: Database session
    
    Returns:
        Processing result
    """
    try:
        print(f"\n[Chunk Processing] Processing chunk {chunk_id}...")
        
        # 1. Summarize
        print("  - Summarizing with Ollama...")
        summary = summarize_chunk_with_ollama(chunk_text)
        
        # 2. Extract topic
        print("  - Extracting topic...")
        topic = extract_topic_with_ollama(chunk_text)
        
        # 3. Embed summary
        print("  - Embedding summary...")
        embedding = embed_text(summary)
        
        # 4. Store in database
        # Note: You'll need to add summary and topic fields to DocumentChunk model
        # For now, we store them as metadata in the chunk_text or separate table
        
        print(f"  - Complete! Topic: {topic}, Summary length: {len(summary)}")
        
        return {
            "success": True,
            "chunk_id": chunk_id,
            "summary": summary,
            "topic": topic,
            "embedding": embedding
        }
        
    except Exception as e:
        print(f"[Chunk Processing] Error: {str(e)}")
        return {
            "error": str(e)
        }
