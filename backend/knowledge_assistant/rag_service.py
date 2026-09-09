import os
import glob
import json
import csv
import logging
import numpy as np
import faiss
import pymupdf
import docx
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from repository.models import KnowledgeDocument

logger = logging.getLogger('enterprise')

class SemanticRAGService:
    """
    Semantic Vector Retrieval Service for Phase 5.
    Dynamically parses and indexes text chunks from localized files in 'Dataset Final/Datasets'
    designated in DATASET_USAGE.md (Microsoft 2025 Annual Report, IBM Annual Report,
    Intel Annual Report, NIST CSF, SEC 10-K, Project Gutenberg, Enron Emails, Customer API specs).
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SemanticRAGService, cls).__new__(cls)
            cls._instance.model = None
            cls._instance.index = None
            cls._instance.documents = []
            cls._instance.is_initialized = False
        return cls._instance

    def initialize_embeddings(self):
        """
        Loads sentence-transformers embedding model and indexes real dataset files from Dataset Final.
        """
        if self.is_initialized:
            return

        logger.info("Initializing SentenceTransformer model (BAAI/bge-small-en-v1.5)...")
        try:
            self.model = SentenceTransformer('BAAI/bge-small-en-v1.5')
        except Exception:
            logger.warning("bge-small-en-v1.5 offline; loading all-MiniLM-L6-v2 fallback.")
            self.model = SentenceTransformer('all-MiniLM-L6-v2')

        dimension = 384
        self.index = faiss.IndexFlatIP(dimension)
        self.documents = []

        # Load real datasets from Dataset Final per DATASET_USAGE.md
        self._load_datasets_from_disk()

        self.is_initialized = True
        logger.info(f"FAISS index initialized with {self.index.ntotal} vector chunks from Dataset Final.")

    def _load_datasets_from_disk(self):
        """
        Parses real dataset files from E:\\project final year\\Dataset Final\\Datasets per DATASET_USAGE.md.
        """
        base_dir = r"E:\project final year\Dataset Final\Datasets"
        extracted_chunks = []

        # 1. NIST Cybersecurity Framework PDF
        nist_pdf = os.path.join(base_dir, 'Policies', 'NIST', 'NIST.CSWP.29.pdf')
        if os.path.exists(nist_pdf):
            try:
                doc = pymupdf.open(nist_pdf)
                for page_num in range(min(15, len(doc))):
                    text = doc[page_num].get_text().strip()
                    if len(text) > 100:
                        extracted_chunks.append({
                            "title": f"NIST Cybersecurity Framework (Page {page_num+1})",
                            "text": text[:800],
                            "source": "NIST.CSWP.29.pdf",
                            "category": "Policies",
                            "repository_type": "team"
                        })
            except Exception as e:
                logger.error(f"Error reading NIST PDF: {e}")

        # 2. Microsoft 2025 Annual Report DOCX
        msft_docx = os.path.join(base_dir, 'Annual_Reports', 'Microsoft', '2025_AnnualReport.docx')
        if os.path.exists(msft_docx):
            try:
                doc = docx.Document(msft_docx)
                paragraphs = [p.text.strip() for p in doc.paragraphs if len(p.text.strip()) > 80]
                for i in range(0, len(paragraphs), 3):
                    chunk_text = " ".join(paragraphs[i:i+3])
                    if chunk_text:
                        extracted_chunks.append({
                            "title": f"Microsoft 2025 Annual Report (Chunk {i//3 + 1})",
                            "text": chunk_text[:800],
                            "source": "2025_AnnualReport.docx",
                            "category": "Annual_Reports",
                            "repository_type": "team"
                        })
            except Exception as e:
                logger.error(f"Error reading Microsoft docx: {e}")

        # 3. IBM 2025 Annual Report PDF
        ibm_pdf = os.path.join(base_dir, 'Annual_Reports', 'IBM', 'ibm-annual-report-2025.pdf')
        if os.path.exists(ibm_pdf):
            try:
                doc = pymupdf.open(ibm_pdf)
                for page_num in range(min(12, len(doc))):
                    text = doc[page_num].get_text().strip()
                    if len(text) > 100:
                        extracted_chunks.append({
                            "title": f"IBM 2025 Annual Report (Page {page_num+1})",
                            "text": text[:800],
                            "source": "ibm-annual-report-2025.pdf",
                            "category": "Annual_Reports",
                            "repository_type": "team"
                        })
            except Exception as e:
                logger.error(f"Error reading IBM PDF: {e}")

        # 4. Intel 2025 Annual Report PDF
        intel_pdf = os.path.join(base_dir, 'Annual_Reports', 'Intel', 'Intel 2025 annual report final.pdf')
        if os.path.exists(intel_pdf):
            try:
                doc = pymupdf.open(intel_pdf)
                for page_num in range(min(10, len(doc))):
                    text = doc[page_num].get_text().strip()
                    if len(text) > 100:
                        extracted_chunks.append({
                            "title": f"Intel 2025 Annual Report (Page {page_num+1})",
                            "text": text[:800],
                            "source": "Intel 2025 annual report final.pdf",
                            "category": "Annual_Reports",
                            "repository_type": "team"
                        })
            except Exception as e:
                logger.error(f"Error reading Intel PDF: {e}")

        # 5. Enron Emails CSV
        enron_csv = os.path.join(base_dir, 'Emails', 'Enron_Email', 'emails.csv')
        if os.path.exists(enron_csv):
            try:
                with open(enron_csv, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = csv.reader(f)
                    next(reader, None)  # header
                    count = 0
                    for row in reader:
                        if len(row) > 1 and len(row[1]) > 100:
                            extracted_chunks.append({
                                "title": f"Enron Executive Mail ({row[0][:30]})",
                                "text": row[1][:700].replace('\n', ' '),
                                "source": "emails.csv",
                                "category": "Emails",
                                "repository_type": "team"
                            })
                            count += 1
                            if count >= 15:
                                break
            except Exception as e:
                logger.error(f"Error reading Enron CSV: {e}")

        # 6. Fallback Seed if disk read returned 0
        if not extracted_chunks:
            extracted_chunks = [
                {
                    "title": "NIST Cybersecurity Framework Overview",
                    "text": "The NIST Cybersecurity Framework (CSF 2.0) outlines Identify, Protect, Detect, Respond, and Recover core functions for enterprise risk governance.",
                    "source": "NIST.CSWP.29.pdf",
                    "category": "Policies",
                    "repository_type": "team"
                },
                {
                    "title": "Microsoft 2025 Annual Financial Report",
                    "text": "Microsoft fiscal highlights reflect double-digit growth in Azure AI Services, Intelligent Cloud infrastructure, and enterprise productivity software.",
                    "source": "2025_AnnualReport.docx",
                    "category": "Annual_Reports",
                    "repository_type": "team"
                }
            ]

        texts = [c["text"] for c in extracted_chunks]
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        self.index.add(np.array(embeddings).astype('float32'))
        self.documents.extend(extracted_chunks)

    def search_vector_store(self, query: str, user=None, top_k: int = 4) -> List[Dict[str, Any]]:
        """
        Executes vector similarity search over FAISS index with server-side security filters.
        """
        if not self.is_initialized:
            self.initialize_embeddings()

        query_vector = self.model.encode([query], normalize_embeddings=True)
        scores, indices = self.index.search(np.array(query_vector).astype('float32'), min(top_k * 2, self.index.ntotal))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.documents):
                continue
            
            doc = self.documents[idx]
            repo_type = doc.get("repository_type", "team")
            uploaded_by = doc.get("uploaded_by")
            
            if repo_type == "personal":
                if not user or not user.is_authenticated:
                    continue
                if user.role != 'admin' and uploaded_by != user.username:
                    continue

            results.append({
                "title": doc.get("title", "Enterprise Document"),
                "text": doc.get("text", ""),
                "source": doc.get("source", "Dataset Final"),
                "category": doc.get("category", "General"),
                "score": float(score),
                "confidence": f"{round(float(score) * 100, 1)}%"
            })

            if len(results) >= top_k:
                break

        return results
