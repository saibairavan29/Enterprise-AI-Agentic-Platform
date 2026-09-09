import os
import json
import logging
import networkx as nx
from typing import List, Dict, Any, Tuple

logger = logging.getLogger('enterprise')

class UniversalKnowledgeGraphService:
    """
    Universal Enterprise Knowledge Graph Service.
    Maintains a domain-independent graph network powered by NetworkX and Django ORM records.
    Provides multi-hop path extraction, entity resolution, and subgraph provenance tracing.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(UniversalKnowledgeGraphService, cls).__new__(cls)
            cls._instance.graph = nx.DiGraph()
            cls._instance.entity_aliases = {}
            cls._instance._is_built = False
        return cls._instance

    def initialize_graph(self, force_rebuild: bool = False):
        """
        Builds or loads the Universal Knowledge Graph from normalized repository records and datasets.
        """
        if self._is_built and not force_rebuild:
            return

        logger.info("Initializing Universal Knowledge Graph...")
        self.graph.clear()
        self.entity_aliases.clear()

        # Seed Core Enterprise Entities & Domain Node Taxonomies
        self._seed_ontology_taxonomies()
        self._is_built = True
        logger.info(f"Universal Knowledge Graph built successfully with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges.")

    def _seed_ontology_taxonomies(self):
        """
        Seeds domain-independent entity nodes and universal relationship edges across all 18 datasets.
        """
        universal_types = [
            "Organization", "Person", "Employee", "Customer", "Supplier",
            "Product", "Department", "Project", "Document", "Policy",
            "Risk", "Metric", "Email", "Transaction"
        ]
        for u_type in universal_types:
            self.graph.add_node(u_type, label=u_type, node_type="Class", provenance="Universal Ontology")

        # Enterprise Node Seeds & Relationships from Datasets
        # Microsoft 2025 Corporate Entity
        self.add_entity("Microsoft Corporation", "Organization", {"ticker": "MSFT", "industry": "Technology"})
        self.add_entity("2025 Annual Report", "Document", {"doc_type": "Annual Report", "year": 2026})
        self.add_relationship("2025 Annual Report", "Microsoft Corporation", "REPORTS_ON", "Microsoft Annual Reports 2025")

        # IBM Corporate Entity
        self.add_entity("IBM Corporation", "Organization", {"ticker": "IBM", "industry": "Enterprise Technology"})
        self.add_entity("IBM 2025 Report", "Document", {"doc_type": "Annual Report"})
        self.add_relationship("IBM 2025 Report", "IBM Corporation", "REPORTS_ON", "IBM Annual Reports 2025")

        # NIST CSWP 29 Policy Framework
        self.add_entity("NIST Cybersecurity Framework", "Policy", {"framework": "NIST CSWP 29"})
        self.add_entity("Risk Management", "Process", {"domain": "Cybersecurity"})
        self.add_relationship("NIST Cybersecurity Framework", "Risk Management", "GOVERNS", "NIST.CSWP.29.pdf")

        # Enron Executive Mail Seed
        self.add_entity("Enron Email Corpus", "Dataset", {"total_emails": 517401})
        self.add_entity("Kenneth Lay", "Person", {"role": "CEO", "company": "Enron"})
        self.add_entity("Jeffrey Skilling", "Person", {"role": "President", "company": "Enron"})
        self.add_relationship("Kenneth Lay", "Jeffrey Skilling", "COMMUNICATED_WITH", "Enron Email Dataset")

        # Seed Dataset Document Nodes & Relationships
        self.add_entity("sample_dirty_hr_dataset.csv", "Dataset", {"domain": "HR Analytics", "type": "CSV"})
        self.add_entity("HR_Dataset.csv", "Dataset", {"domain": "HR Analytics", "type": "CSV"})
        self.add_entity("Procurement KPI Analysis Dataset.csv", "Dataset", {"domain": "Supply Chain", "type": "CSV"})
        self.add_entity("Sample - Superstore.csv", "Dataset", {"domain": "Sales", "type": "CSV"})
        self.add_entity("fake_job_postings.csv", "Dataset", {"domain": "Data Quality", "type": "CSV"})

        self.add_relationship("sample_dirty_hr_dataset.csv", "Production", "GOVERNS_ROSTER", "Dataset Final")
        self.add_relationship("HR_Dataset.csv", "Production", "GOVERNS_ROSTER", "Dataset Final")
        self.add_relationship("Procurement KPI Analysis Dataset.csv", "Procurement Department", "BELONGS_TO", "Dataset Final")
        self.add_relationship("Sample - Superstore.csv", "Organization", "BELONGS_TO", "Dataset Final")

        # Dynamic KnowledgeRecord HR Employee Seeds from Django ORM
        try:
            from repository.models import KnowledgeRecord
            for rec in KnowledgeRecord.objects.all()[:100]:
                cdata = rec.canonical_data or {}
                afields = rec.additional_fields or {}
                emp_id = cdata.get('employee_id')
                emp_name = afields.get('Employee_Name') or f"Employee {emp_id}"
                dept = cdata.get('department') or afields.get('Department') or "Production"
                
                if emp_id:
                    emp_node = f"Employee {emp_id} ({emp_name})"
                    self.add_entity(emp_node, "Employee", {
                        "emp_id": emp_id,
                        "name": emp_name,
                        "salary": cdata.get('salary'),
                        "department": dept,
                        "position": afields.get('Position'),
                        "status": afields.get('EmploymentStatus'),
                        "perf_score": afields.get('PerformanceScore')
                    })
                    self.add_entity(str(emp_id), "EmployeeID", {"canonical": emp_node})
                    self.add_relationship(str(emp_id), emp_node, "IDENTIFIES", "HR Dataset")

                    self.add_entity(dept, "Department")
                    self.add_relationship(emp_node, dept, "WORKS_IN", "HR Dataset")

                    mgr = afields.get('ManagerName')
                    if mgr:
                        self.add_entity(mgr, "Person", {"role": "Manager"})
                        self.add_relationship(emp_node, mgr, "REPORTS_TO", "HR Dataset")
        except Exception as e:
            logger.error(f"Error seeding HR records into Universal Knowledge Graph: {e}")

    def add_entity(self, name: str, entity_type: str, attributes: Dict[str, Any] = None):
        """
        Adds or updates an entity node in the Universal Knowledge Graph.
        """
        canonical_name = self.resolve_entity_name(name)
        if not self.graph.has_node(canonical_name):
            self.graph.add_node(
                canonical_name,
                name=canonical_name,
                entity_type=entity_type,
                attributes=attributes or {},
                aliases=[name]
            )
        else:
            node_data = self.graph.nodes[canonical_name]
            if name not in node_data.get('aliases', []):
                node_data.setdefault('aliases', []).append(name)
            if attributes:
                node_data['attributes'].update(attributes)
        
        self.entity_aliases[name.lower()] = canonical_name
        return canonical_name

    def add_relationship(self, source_name: str, target_name: str, rel_type: str, provenance: str, attributes: Dict[str, Any] = None):
        """
        Adds a directed semantic relationship edge between two entities.
        """
        source = self.add_entity(source_name, "Concept")
        target = self.add_entity(target_name, "Concept")
        
        self.graph.add_edge(
            source,
            target,
            relationship_type=rel_type,
            provenance=provenance,
            attributes=attributes or {}
        )

    def resolve_entity_name(self, raw_name: str) -> str:
        """
        Entity Resolution: Maps variant names or synonyms to canonical entity names.
        """
        cleaned = str(raw_name).strip()
        lower = cleaned.lower()
        
        synonym_map = {
            "microsoft": "Microsoft Corporation",
            "msft": "Microsoft Corporation",
            "ibm": "IBM Corporation",
            "nist": "NIST Cybersecurity Framework",
            "enron": "Enron Email Corpus",
        }
        if lower in synonym_map:
            return synonym_map[lower]
        
        # Alias lookup
        for node, data in self.graph.nodes(data=True):
            aliases = [str(a).lower() for a in data.get('aliases', [])]
            if lower == str(node).lower() or lower in aliases:
                return str(node)

        return self.entity_aliases.get(lower, cleaned)

    def extract_candidate_entities(self, query_text: str) -> List[str]:
        """
        Extracts and resolves candidate concept entities from query text.
        """
        import re
        query_lower = query_text.lower()
        stopwords = {
            "the", "a", "an", "and", "or", "in", "on", "for", "to", "of", "with", "by", "at", "from",
            "employee", "employees", "dataset", "number", "total", "give", "tell", "status", "active",
            "inactive", "percentage", "csv", "xlsx", "pdf", "what", "who", "which", "how", "many", "much", "is", "are",
            "read", "this", "document", "carefully", "explain", "contains", "report", "relationship", "between"
        }
        words = [w for w in re.findall(r'\b\w+\b', query_lower) if len(w) >= 3 and w not in stopwords]
        
        resolved_entities = []
        for w in words:
            resolved = self.resolve_entity_name(w)
            if self.graph.has_node(resolved) and resolved not in resolved_entities:
                resolved_entities.append(resolved)

        # Fallback substring node search
        if not resolved_entities and words:
            for node in self.graph.nodes():
                node_str = str(node).lower()
                if any(w in node_str for w in words):
                    if node not in resolved_entities:
                        resolved_entities.append(node)

        return resolved_entities

    def search_graph(self, query_text: str, max_depth: int = 2, document_scope: str = None, is_document_scoped: bool = False) -> List[Dict[str, Any]]:
        """
        Performs query-relevant entity resolution, subgraph extraction, relationship scoring,
        and returns structured KG evidence items.
        """
        if not self._is_built:
            self.initialize_graph()

        candidate_entities = self.extract_candidate_entities(query_text)

        # Fallback ONLY for global enterprise-wide queries when no specific node matched
        if not candidate_entities and not is_document_scoped and not document_scope:
            for node in self.graph.nodes():
                node_str = str(node).lower()
                if any(kw in node_str for kw in ["sample_dirty_hr_dataset", "hr_dataset", "dataset", "organization", "policy", "procurement", "2025"]):
                    candidate_entities.append(node)

        scored_evidence = []
        seen_edges = set()

        for source_node in candidate_entities[:4]:
            # Inspect 1-hop and 2-hop edges originating from or pointing to candidate entities
            neighbors = list(self.graph.successors(source_node)) + list(self.graph.predecessors(source_node))
            
            for target_node in neighbors:
                if source_node == target_node:
                    continue

                edge_pairs = []
                if self.graph.has_edge(source_node, target_node):
                    edge_pairs.append((source_node, target_node))
                if self.graph.has_edge(target_node, source_node):
                    edge_pairs.append((target_node, source_node))

                for u, v in edge_pairs:
                    edge_key = (u, v)
                    if edge_key in seen_edges:
                        continue
                    seen_edges.add(edge_key)

                    edge_data = self.graph.get_edge_data(u, v, default={})
                    rel_type = edge_data.get("relationship_type", "RELATED_TO")
                    provenance = edge_data.get("provenance", document_scope or "Enterprise Knowledge Base")

                    # Enforce strict document scoping on KG evidence
                    if is_document_scoped and document_scope:
                        doc_scope_clean = document_scope.lower().strip()
                        prov_clean = str(provenance).lower().strip()
                        # Allow if provenance matches document_scope or universal ontology
                        if doc_scope_clean not in prov_clean and "universal" not in prov_clean:
                            continue

                    # Query Relevance Scoring
                    query_lower = query_text.lower()
                    relevance_score = 0.5
                    if str(u).lower() in query_lower:
                        relevance_score += 0.25
                    if str(v).lower() in query_lower:
                        relevance_score += 0.25
                    if rel_type.lower() in query_lower:
                        relevance_score += 0.2

                    confidence_val = min(0.98, max(0.70, relevance_score))
                    confidence_pct = f"{round(confidence_val * 100, 1)}%"

                    why_matters = f"Connects entity '{u}' to '{v}' via relationship [{rel_type}]."
                    path_str = f"{u} -[{rel_type}]-> {v}"
                    fact_stmt = f"Entity '{u}' has relationship '{rel_type}' with entity '{v}' (Source: {provenance})."

                    evidence_item = {
                        "source_entity": u,
                        "relationship": rel_type,
                        "target_entity": v,
                        "provenance": provenance,
                        "why_it_matters": why_matters,
                        "confidence": confidence_pct,
                        "relevance_score": round(relevance_score, 2),
                        "path_string": path_str,
                        "fact_statement": fact_stmt,
                        "edges": [{
                            "source": u,
                            "relationship": rel_type,
                            "target": v,
                            "provenance": provenance
                        }],
                        "length": 1,
                        "source": provenance
                    }
                    scored_evidence.append(evidence_item)

        # Sort by relevance score descending
        scored_evidence.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        return scored_evidence[:5]


