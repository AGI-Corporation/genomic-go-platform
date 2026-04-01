"""
Literature Mining Module for Genomic.go Platform

Provides automated scientific literature retrieval and knowledge extraction from:
- PubMed / MEDLINE (via NCBI E-utilities REST API)
- bioRxiv / medRxiv (via Crossref API)
- Citation network construction and analysis

Author: AGI Corporation Platform Team
Version: 1.0.0
"""

import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------


@dataclass
class Article:
    """Scientific article metadata."""

    article_id: str
    title: str
    abstract: str
    authors: List[str]
    journal: str
    publication_date: str
    doi: Optional[str] = None
    pmid: Optional[str] = None
    source: str = "pubmed"
    keywords: List[str] = field(default_factory=list)
    citations: int = 0
    relevance_score: float = 0.0
    full_text_url: Optional[str] = None


@dataclass
class ExtractedEntity:
    """Biomedical entity extracted from text."""

    text: str
    entity_type: str   # "gene", "protein", "disease", "drug", "pathway"
    start_char: int
    end_char: int
    confidence: float
    normalized_id: Optional[str] = None  # e.g., HGNC gene ID


@dataclass
class CitationEdge:
    """Directed edge in the citation network."""

    citing_id: str
    cited_id: str
    weight: float = 1.0


@dataclass
class LiteratureReview:
    """Compiled literature review for a research query."""

    query: str
    articles: List[Article]
    key_entities: List[ExtractedEntity]
    citation_network: List[CitationEdge]
    knowledge_summary: str
    search_date: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_found: int = 0


# ---------------------------------------------------------------------------
# PubMed Client
# ---------------------------------------------------------------------------


class PubMedClient:
    """
    NCBI E-utilities API client for PubMed searches.

    Rate-limits requests to 3/second per NCBI guidelines (10/second with API key).
    """

    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    _MIN_REQUEST_INTERVAL = 0.35  # seconds between requests

    def __init__(self, api_key: Optional[str] = None, timeout: int = 30):
        """
        Args:
            api_key: NCBI API key (allows higher rate limits).
            timeout: HTTP request timeout in seconds.
        """
        self.api_key = api_key
        self.timeout = timeout
        self._last_request_time = 0.0
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "GenomicGo/1.0 (research@agicorp.network)"})

    def search(
        self,
        query: str,
        max_results: int = 20,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        sort: str = "relevance",
    ) -> List[str]:
        """
        Search PubMed and return a list of PMIDs.

        Args:
            query: PubMed search query (supports MeSH terms, boolean operators).
            max_results: Maximum number of PMIDs to retrieve.
            date_from: Start date filter (YYYY/MM/DD format).
            date_to: End date filter (YYYY/MM/DD format).
            sort: Sort order ('relevance' or 'pub_date').

        Returns:
            List of PubMed IDs (PMIDs) as strings.
        """
        self._rate_limit()

        params: Dict = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": sort,
        }
        if self.api_key:
            params["api_key"] = self.api_key
        if date_from:
            params["mindate"] = date_from
        if date_to:
            params["maxdate"] = date_to

        try:
            response = self.session.get(
                f"{self.BASE_URL}/esearch.fcgi",
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            pmids = data.get("esearchresult", {}).get("idlist", [])
            logger.info(f"PubMed search returned {len(pmids)} results for: {query[:60]}")
            return pmids
        except requests.RequestException as exc:
            logger.error(f"PubMed search failed: {exc}")
            return []

    def fetch_articles(self, pmids: List[str]) -> List[Article]:
        """
        Fetch full article metadata for a list of PMIDs.

        Args:
            pmids: List of PubMed IDs to fetch.

        Returns:
            List of Article objects with metadata.
        """
        if not pmids:
            return []

        self._rate_limit()

        params: Dict = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "rettype": "abstract",
        }
        if self.api_key:
            params["api_key"] = self.api_key

        try:
            response = self.session.get(
                f"{self.BASE_URL}/efetch.fcgi",
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return self._parse_xml_response(response.text, pmids)
        except requests.RequestException as exc:
            logger.error(f"PubMed fetch failed: {exc}")
            return []

    def _parse_xml_response(self, xml_text: str, pmids: List[str]) -> List[Article]:
        """Parse PubMed XML response into Article objects."""
        articles = []

        # Extract article blocks using regex (avoids lxml dependency)
        article_pattern = re.compile(
            r"<PubmedArticle>(.*?)</PubmedArticle>", re.DOTALL
        )

        for i, match in enumerate(article_pattern.finditer(xml_text)):
            block = match.group(1)
            pmid = i < len(pmids) and pmids[i] or self._extract_tag(block, "PMID")

            title = self._extract_tag(block, "ArticleTitle") or "No title"
            abstract = self._extract_tag(block, "AbstractText") or ""
            journal = self._extract_tag(block, "Title") or "Unknown Journal"

            # Authors
            author_pattern = re.compile(
                r"<Author[^>]*>.*?<LastName>(.*?)</LastName>.*?</Author>",
                re.DOTALL,
            )
            authors = [m.group(1) for m in author_pattern.finditer(block)]

            # Publication date
            year = self._extract_tag(block, "Year") or "2024"
            month = self._extract_tag(block, "Month") or "01"
            pub_date = f"{year}/{month}"

            # DOI
            doi_match = re.search(r'IdType="doi"[^>]*>(.*?)</ArticleId>', block)
            doi = doi_match.group(1) if doi_match else None

            # Keywords
            kw_pattern = re.compile(r"<Keyword[^>]*>(.*?)</Keyword>", re.DOTALL)
            keywords = [m.group(1).strip() for m in kw_pattern.finditer(block)]

            articles.append(
                Article(
                    article_id=str(pmid),
                    title=self._clean_text(title),
                    abstract=self._clean_text(abstract),
                    authors=authors[:10],
                    journal=self._clean_text(journal),
                    publication_date=pub_date,
                    doi=doi,
                    pmid=str(pmid),
                    source="pubmed",
                    keywords=keywords[:20],
                )
            )

        return articles

    @staticmethod
    def _extract_tag(text: str, tag: str) -> Optional[str]:
        """Extract text content of first occurrence of an XML tag."""
        match = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", text, re.DOTALL)
        return match.group(1).strip() if match else None

    @staticmethod
    def _clean_text(text: str) -> str:
        """Remove XML tags and normalize whitespace."""
        clean = re.sub(r"<[^>]+>", "", text)
        return " ".join(clean.split())

    def _rate_limit(self) -> None:
        """Enforce minimum time between API requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._MIN_REQUEST_INTERVAL:
            time.sleep(self._MIN_REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.time()


# ---------------------------------------------------------------------------
# bioRxiv Client
# ---------------------------------------------------------------------------


class BioRxivClient:
    """
    Client for bioRxiv/medRxiv preprint retrieval via Crossref API.

    Supports searching by keyword, date range, and category.
    """

    BIORXIV_API = "https://api.biorxiv.org/details/biorxiv"
    CROSSREF_API = "https://api.crossref.org/works"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "GenomicGo/1.0 (mailto:research@agicorp.network)"}
        )

    def search(
        self,
        query: str,
        max_results: int = 10,
        date_from: str = "2020-01-01",
    ) -> List[Article]:
        """
        Search bioRxiv via Crossref API.

        Args:
            query: Search query string.
            max_results: Maximum number of preprints to return.
            date_from: Filter preprints published after this date (YYYY-MM-DD).

        Returns:
            List of Article objects for matching preprints.
        """
        try:
            params = {
                "query": query,
                "filter": f"from-pub-date:{date_from},type:posted-content",
                "rows": max_results,
                "select": "DOI,title,abstract,author,published,container-title",
                "sort": "relevance",
            }

            response = self.session.get(
                self.CROSSREF_API,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            items = data.get("message", {}).get("items", [])
            logger.info(f"bioRxiv search returned {len(items)} results")
            return [self._parse_crossref_item(item) for item in items]
        except requests.RequestException as exc:
            logger.error(f"bioRxiv search failed: {exc}")
            return []

    def _parse_crossref_item(self, item: Dict) -> Article:
        """Convert Crossref item dict to Article object."""
        doi = item.get("DOI", "")
        title_list = item.get("title", ["No title"])
        title = title_list[0] if title_list else "No title"

        abstract = item.get("abstract", "")
        abstract = re.sub(r"<[^>]+>", "", abstract)  # Strip JATS XML tags

        authors_raw = item.get("author", [])
        authors = [
            f"{a.get('given', '')} {a.get('family', '')}".strip()
            for a in authors_raw[:10]
        ]

        journal_list = item.get("container-title", ["bioRxiv"])
        journal = journal_list[0] if journal_list else "bioRxiv"

        pub_date_parts = item.get("published", {}).get("date-parts", [[2024]])
        pub_date = "-".join(str(p) for p in pub_date_parts[0]) if pub_date_parts else "2024"

        return Article(
            article_id=doi,
            title=title,
            abstract=abstract[:2000],
            authors=authors,
            journal=journal,
            publication_date=pub_date,
            doi=doi,
            source="biorxiv",
            full_text_url=f"https://doi.org/{doi}" if doi else None,
        )


# ---------------------------------------------------------------------------
# Biomedical NER (Named Entity Recognition)
# ---------------------------------------------------------------------------


class BiomedicalNER:
    """
    Rule-based biomedical named entity recognition.

    In production this wraps BioBERT or SciSpacy NER models.
    Here we provide a comprehensive pattern-matching implementation.
    """

    # Common gene/protein symbols
    GENE_PATTERNS = [
        r"\b(BRCA[12]|APOE|TP53|EGFR|KRAS|BRAF|ALK|MET|HER2|VEGF[A-Z]?|"
        r"PTEN|RB1|CDK[0-9]+|MDM2|BCL2|MYC|AKT[0-9]?|PIK3CA|MTOR)\b",
        r"\b[A-Z][A-Z0-9]{2,8}\d\b",  # Generic gene pattern (e.g., CDK4, HIF1A)
    ]

    # Disease terms
    DISEASE_PATTERNS = [
        r"\b(Alzheimer['\u2019]?s disease|Parkinson['\u2019]?s disease|"
        r"cancer|carcinoma|adenocarcinoma|glioma|leukemia|lymphoma|"
        r"diabetes|hypertension|heart failure|COPD|asthma|depression)\b",
    ]

    # Drug/compound terms
    DRUG_PATTERNS = [
        r"\b(imatinib|erlotinib|gefitinib|osimertinib|pembrolizumab|"
        r"nivolumab|trastuzumab|bevacizumab|metformin|atorvastatin|"
        r"aspirin|paclitaxel|doxorubicin|cisplatin|olaparib)\b",
        r"\b[A-Z][a-z]+(mab|nib|zumab|tinib|ciclib)\b",  # Systematic naming
    ]

    # Pathway/biological process terms
    PATHWAY_PATTERNS = [
        r"\b(PI3K[/-]AKT|MAPK|NF-κB|Wnt|Hedgehog|Notch|JAK[/-]STAT|"
        r"mTOR|p53|VEGF|TGF-β|apoptosis|autophagy|senescence|"
        r"glycolysis|oxidative phosphorylation)\b",
    ]

    def extract_entities(self, text: str) -> List[ExtractedEntity]:
        """
        Extract biomedical entities from text.

        Args:
            text: Input text (abstract, full text, etc.).

        Returns:
            List of ExtractedEntity sorted by position.
        """
        entities: List[ExtractedEntity] = []
        seen_spans: set = set()

        patterns_by_type = [
            (self.GENE_PATTERNS, "gene"),
            (self.DISEASE_PATTERNS, "disease"),
            (self.DRUG_PATTERNS, "drug"),
            (self.PATHWAY_PATTERNS, "pathway"),
        ]

        for pattern_list, entity_type in patterns_by_type:
            for pattern in pattern_list:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    span = (match.start(), match.end())
                    if span in seen_spans:
                        continue
                    seen_spans.add(span)

                    entities.append(
                        ExtractedEntity(
                            text=match.group(),
                            entity_type=entity_type,
                            start_char=match.start(),
                            end_char=match.end(),
                            confidence=0.85 if entity_type in ("gene", "drug") else 0.75,
                        )
                    )

        entities.sort(key=lambda e: e.start_char)
        return entities

    def aggregate_entities(
        self, articles: List[Article]
    ) -> List[Tuple[str, str, int]]:
        """
        Aggregate entity mentions across multiple articles.

        Args:
            articles: List of articles to mine.

        Returns:
            List of (entity_text, entity_type, mention_count) sorted by frequency.
        """
        entity_counts: Dict[Tuple[str, str], int] = {}

        for article in articles:
            text = f"{article.title} {article.abstract}"
            entities = self.extract_entities(text)
            for entity in entities:
                key = (entity.text.upper(), entity.entity_type)
                entity_counts[key] = entity_counts.get(key, 0) + 1

        results = [
            (text, etype, count)
            for (text, etype), count in entity_counts.items()
        ]
        results.sort(key=lambda x: x[2], reverse=True)
        return results


# ---------------------------------------------------------------------------
# Citation Network Builder
# ---------------------------------------------------------------------------


class CitationNetworkBuilder:
    """
    Constructs and analyzes citation networks from article metadata.

    Implements PageRank-based influence scoring.
    """

    def __init__(self, damping_factor: float = 0.85, max_iterations: int = 100):
        """
        Args:
            damping_factor: PageRank damping factor.
            max_iterations: Maximum PageRank iterations.
        """
        self.damping_factor = damping_factor
        self.max_iterations = max_iterations

    def build_network(self, articles: List[Article]) -> List[CitationEdge]:
        """
        Build citation edges using reference co-occurrence heuristics.

        Args:
            articles: List of articles to analyze.

        Returns:
            List of CitationEdge representing the citation graph.
        """
        edges: List[CitationEdge] = []
        article_ids = {a.article_id for a in articles}

        # Build co-authorship + keyword proximity edges as citation proxies
        for i, article_a in enumerate(articles):
            for j, article_b in enumerate(articles):
                if i >= j:
                    continue

                weight = self._compute_similarity_weight(article_a, article_b)
                if weight > 0.1:
                    edges.append(
                        CitationEdge(
                            citing_id=article_a.article_id,
                            cited_id=article_b.article_id,
                            weight=weight,
                        )
                    )

        return edges

    def _compute_similarity_weight(
        self, article_a: Article, article_b: Article
    ) -> float:
        """Compute similarity weight between two articles."""
        weight = 0.0

        # Shared keywords
        shared_kw = set(article_a.keywords) & set(article_b.keywords)
        weight += len(shared_kw) * 0.2

        # Shared authors
        authors_a = set(article_a.authors)
        authors_b = set(article_b.authors)
        shared_auth = authors_a & authors_b
        weight += len(shared_auth) * 0.3

        # Title word overlap
        words_a = set(article_a.title.lower().split())
        words_b = set(article_b.title.lower().split())
        stopwords = {"the", "a", "an", "of", "in", "and", "to", "for", "with"}
        content_a = words_a - stopwords
        content_b = words_b - stopwords
        if content_a and content_b:
            overlap = len(content_a & content_b) / len(content_a | content_b)
            weight += overlap * 0.5

        return min(weight, 1.0)

    def compute_pagerank(
        self, articles: List[Article], edges: List[CitationEdge]
    ) -> Dict[str, float]:
        """
        Compute PageRank scores for articles in the citation network.

        Args:
            articles: List of articles (nodes).
            edges: List of citation edges.

        Returns:
            Dict mapping article_id to PageRank score.
        """
        if not articles:
            return {}

        ids = [a.article_id for a in articles]
        n = len(ids)
        id_to_idx = {aid: i for i, aid in enumerate(ids)}

        # Build adjacency: in-links for each node
        in_links: Dict[int, List[int]] = {i: [] for i in range(n)}
        out_degree: Dict[int, int] = {i: 0 for i in range(n)}

        for edge in edges:
            src = id_to_idx.get(edge.citing_id)
            dst = id_to_idx.get(edge.cited_id)
            if src is not None and dst is not None:
                in_links[dst].append(src)
                out_degree[src] += 1

        # Initialize PageRank
        pr = {i: 1.0 / n for i in range(n)}

        for _ in range(self.max_iterations):
            new_pr = {}
            for i in range(n):
                incoming = sum(
                    pr[j] / out_degree[j]
                    for j in in_links[i]
                    if out_degree[j] > 0
                )
                new_pr[i] = (1 - self.damping_factor) / n + self.damping_factor * incoming

            # Check convergence
            diff = sum(abs(new_pr[i] - pr[i]) for i in range(n))
            pr = new_pr
            if diff < 1e-6:
                break

        return {ids[i]: round(pr[i], 6) for i in range(n)}


# ---------------------------------------------------------------------------
# Literature Miner (Main Orchestrator)
# ---------------------------------------------------------------------------


class LiteratureMiner:
    """
    High-level literature mining orchestrator for Genomic.go Platform.

    Combines PubMed, bioRxiv, NER, and citation analysis into a unified
    research literature review pipeline.
    """

    def __init__(
        self,
        pubmed_api_key: Optional[str] = None,
        include_preprints: bool = True,
        timeout: int = 30,
    ):
        """
        Args:
            pubmed_api_key: Optional NCBI API key for higher rate limits.
            include_preprints: Whether to also search bioRxiv/medRxiv.
            timeout: HTTP timeout for API calls.
        """
        self.pubmed = PubMedClient(api_key=pubmed_api_key, timeout=timeout)
        self.biorxiv = BioRxivClient(timeout=timeout)
        self.ner = BiomedicalNER()
        self.citation_builder = CitationNetworkBuilder()
        self.include_preprints = include_preprints

    def mine(
        self,
        query: str,
        max_pubmed: int = 20,
        max_preprints: int = 10,
        date_from: Optional[str] = None,
    ) -> LiteratureReview:
        """
        Execute a complete literature mining pipeline.

        Args:
            query: Research query (supports PubMed MeSH + boolean syntax).
            max_pubmed: Maximum PubMed articles to retrieve.
            max_preprints: Maximum bioRxiv preprints to retrieve.
            date_from: Start date filter (YYYY-MM-DD or YYYY/MM/DD).

        Returns:
            LiteratureReview with ranked articles, entities, and citation network.
        """
        logger.info(f"Starting literature mining for: {query}")

        # 1. Retrieve articles
        articles = self._retrieve_articles(query, max_pubmed, max_preprints, date_from)
        logger.info(f"Retrieved {len(articles)} total articles")

        # 2. Score relevance
        articles = self._score_relevance(articles, query)
        articles.sort(key=lambda a: a.relevance_score, reverse=True)

        # 3. Extract biomedical entities
        all_text = " ".join(f"{a.title} {a.abstract}" for a in articles[:50])
        entities = self.ner.extract_entities(all_text)
        entity_summary = self.ner.aggregate_entities(articles)

        # Convert to ExtractedEntity list (top 50 by frequency)
        top_entities = [
            ExtractedEntity(
                text=text,
                entity_type=etype,
                start_char=0,
                end_char=len(text),
                confidence=min(1.0, count / 10.0),
            )
            for text, etype, count in entity_summary[:50]
        ]

        # 4. Build citation network
        edges = self.citation_builder.build_network(articles[:100])
        pagerank = self.citation_builder.compute_pagerank(articles[:100], edges)

        # Update citation importance scores
        for article in articles:
            if article.article_id in pagerank:
                article.relevance_score = (
                    article.relevance_score * 0.7 + pagerank[article.article_id] * 100 * 0.3
                )

        articles.sort(key=lambda a: a.relevance_score, reverse=True)

        # 5. Generate knowledge summary
        summary = self._generate_summary(query, articles[:10], entity_summary[:10])

        return LiteratureReview(
            query=query,
            articles=articles,
            key_entities=top_entities,
            citation_network=edges,
            knowledge_summary=summary,
            total_found=len(articles),
        )

    def _retrieve_articles(
        self,
        query: str,
        max_pubmed: int,
        max_preprints: int,
        date_from: Optional[str],
    ) -> List[Article]:
        """Retrieve articles from all configured sources."""
        articles: List[Article] = []

        # PubMed
        pubmed_date = date_from.replace("-", "/") if date_from else None
        pmids = self.pubmed.search(query, max_results=max_pubmed, date_from=pubmed_date)
        if pmids:
            pubmed_articles = self.pubmed.fetch_articles(pmids)
            articles.extend(pubmed_articles)

        # bioRxiv / Preprints
        if self.include_preprints:
            preprint_date = date_from or "2020-01-01"
            preprints = self.biorxiv.search(
                query, max_results=max_preprints, date_from=preprint_date
            )
            articles.extend(preprints)

        return articles

    def _score_relevance(self, articles: List[Article], query: str) -> List[Article]:
        """
        Score article relevance to the query using TF-IDF-inspired keyword matching.

        Args:
            articles: Articles to score.
            query: Research query.

        Returns:
            Articles with relevance_score populated.
        """
        query_terms = set(query.lower().split())

        for article in articles:
            text = f"{article.title} {article.abstract}".lower()
            words = set(text.split())

            # Term frequency
            term_hits = sum(1 for term in query_terms if term in words)
            tf_score = term_hits / max(1, len(query_terms))

            # Title bonus (title match is more informative)
            title_words = set(article.title.lower().split())
            title_hits = sum(1 for term in query_terms if term in title_words)
            title_bonus = title_hits / max(1, len(query_terms)) * 0.5

            # Keyword bonus
            article_kw_lower = {kw.lower() for kw in article.keywords}
            kw_hits = sum(1 for term in query_terms if term in article_kw_lower)
            kw_bonus = kw_hits / max(1, len(query_terms)) * 0.3

            article.relevance_score = round(tf_score + title_bonus + kw_bonus, 4)

        return articles

    def _generate_summary(
        self,
        query: str,
        top_articles: List[Article],
        entity_summary: List[Tuple[str, str, int]],
    ) -> str:
        """Generate a structured text summary of the literature review."""
        lines = [f"Literature Review Summary: {query}\n"]
        lines.append(f"Analyzed {len(top_articles)} top articles.\n")

        if top_articles:
            lines.append("Most Relevant Articles:")
            for i, art in enumerate(top_articles[:5], 1):
                first_author = art.authors[0] if art.authors else "Unknown"
                lines.append(
                    f"  {i}. {art.title} ({first_author} et al., "
                    f"{art.publication_date[:4]})"
                )

        if entity_summary:
            genes = [e for e in entity_summary if e[1] == "gene"][:5]
            drugs = [e for e in entity_summary if e[1] == "drug"][:5]
            diseases = [e for e in entity_summary if e[1] == "disease"][:3]

            if genes:
                lines.append(
                    "\nKey Genes/Proteins: "
                    + ", ".join(f"{g[0]} ({g[2]} mentions)" for g in genes)
                )
            if drugs:
                lines.append(
                    "Key Drugs/Compounds: "
                    + ", ".join(f"{d[0]} ({d[2]} mentions)" for d in drugs)
                )
            if diseases:
                lines.append(
                    "Key Diseases: "
                    + ", ".join(f"{d[0]} ({d[2]} mentions)" for d in diseases)
                )

        return "\n".join(lines)

    def get_top_entities_by_type(
        self, review: LiteratureReview, entity_type: str, top_n: int = 10
    ) -> List[ExtractedEntity]:
        """Filter entities from a review by type and return top N."""
        filtered = [e for e in review.key_entities if e.entity_type == entity_type]
        return sorted(filtered, key=lambda e: e.confidence, reverse=True)[:top_n]
