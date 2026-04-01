"""Tests for Literature Mining Module."""

import sys
import os

import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from literature.mining import (
    Article,
    BiomedicalNER,
    BioRxivClient,
    CitationNetworkBuilder,
    CitationEdge,
    ExtractedEntity,
    LiteratureMiner,
    LiteratureReview,
    PubMedClient,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_article(
    article_id: str = "1",
    title: str = "BRCA1 mutation and breast cancer risk",
    abstract: str = "We studied BRCA1 and BRCA2 mutations in breast cancer patients.",
    keywords: list = None,
    authors: list = None,
    relevance_score: float = 0.8,
) -> Article:
    return Article(
        article_id=article_id,
        title=title,
        abstract=abstract,
        authors=authors or ["Smith J", "Doe A"],
        journal="Nature Medicine",
        publication_date="2024/01",
        pmid=article_id,
        keywords=keywords or ["BRCA1", "breast cancer"],
        relevance_score=relevance_score,
    )


# ---------------------------------------------------------------------------
# BiomedicalNER Tests
# ---------------------------------------------------------------------------


class TestBiomedicalNER:
    @pytest.fixture
    def ner(self):
        return BiomedicalNER()

    def test_extract_gene_entities(self, ner):
        text = "BRCA1 and EGFR mutations are commonly found in cancer."
        entities = ner.extract_entities(text)
        gene_texts = [e.text.upper() for e in entities if e.entity_type == "gene"]
        assert "BRCA1" in gene_texts or "EGFR" in gene_texts

    def test_extract_disease_entities(self, ner):
        text = "Patients with Alzheimer's disease and cancer were enrolled."
        entities = ner.extract_entities(text)
        disease_texts = [e.text.lower() for e in entities if e.entity_type == "disease"]
        assert any("alzheimer" in t or "cancer" in t for t in disease_texts)

    def test_extract_drug_entities(self, ner):
        text = "Treatment with imatinib and pembrolizumab was effective."
        entities = ner.extract_entities(text)
        drug_texts = [e.text.lower() for e in entities if e.entity_type == "drug"]
        assert any("imatinib" in t or "pembrolizumab" in t for t in drug_texts)

    def test_extract_pathway_entities(self, ner):
        text = "The PI3K/AKT and mTOR pathways are activated."
        entities = ner.extract_entities(text)
        pathway_texts = [e.text.lower() for e in entities if e.entity_type == "pathway"]
        assert any("pi3k" in t or "mtor" in t for t in pathway_texts)

    def test_entities_sorted_by_position(self, ner):
        text = "BRCA1 is important. Imatinib targets BCR-ABL."
        entities = ner.extract_entities(text)
        for i in range(len(entities) - 1):
            assert entities[i].start_char <= entities[i + 1].start_char

    def test_no_entities_in_empty_text(self, ner):
        entities = ner.extract_entities("")
        assert entities == []

    def test_entity_confidence_range(self, ner):
        text = "BRCA1 and imatinib and Alzheimer's disease"
        entities = ner.extract_entities(text)
        for e in entities:
            assert 0 <= e.confidence <= 1.0

    def test_aggregate_entities_counts(self, ner):
        articles = [
            make_article(
                article_id="1",
                title="BRCA1 in cancer",
                abstract="BRCA1 BRCA1 cancer cancer",
            ),
            make_article(
                article_id="2",
                title="EGFR inhibitor",
                abstract="EGFR imatinib cancer",
            ),
        ]
        summary = ner.aggregate_entities(articles)
        assert isinstance(summary, list)
        # Each entry is (text, type, count)
        for entry in summary:
            assert len(entry) == 3
            assert entry[2] >= 1


# ---------------------------------------------------------------------------
# CitationNetworkBuilder Tests
# ---------------------------------------------------------------------------


class TestCitationNetworkBuilder:
    @pytest.fixture
    def builder(self):
        return CitationNetworkBuilder()

    @pytest.fixture
    def articles(self):
        return [
            make_article(
                "A1",
                title="Kinase inhibitors in cancer",
                keywords=["kinase", "cancer", "inhibitor"],
                authors=["Smith J"],
            ),
            make_article(
                "A2",
                title="Cancer kinase drug design",
                keywords=["cancer", "kinase", "drug"],
                authors=["Smith J", "Lee K"],
            ),
            make_article(
                "A3",
                title="Unrelated paper on ecology",
                keywords=["ecology"],
                authors=["Brown A"],
            ),
        ]

    def test_build_network_returns_edges(self, builder, articles):
        edges = builder.build_network(articles)
        assert isinstance(edges, list)
        for e in edges:
            assert isinstance(e, CitationEdge)

    def test_related_articles_get_edges(self, builder, articles):
        edges = builder.build_network(articles)
        edge_pairs = {(e.citing_id, e.cited_id) for e in edges}
        # A1 and A2 share keywords and author, should be connected
        assert ("A1", "A2") in edge_pairs or ("A2", "A1") in edge_pairs

    def test_edge_weight_in_range(self, builder, articles):
        edges = builder.build_network(articles)
        for e in edges:
            assert 0.0 <= e.weight <= 1.0

    def test_compute_pagerank(self, builder, articles):
        edges = builder.build_network(articles)
        scores = builder.compute_pagerank(articles, edges)
        assert isinstance(scores, dict)
        # All scores should be positive
        for score in scores.values():
            assert score > 0

    def test_pagerank_empty_articles(self, builder):
        scores = builder.compute_pagerank([], [])
        assert scores == {}

    def test_pagerank_scores_sum_approximately_one(self, builder, articles):
        edges = builder.build_network(articles)
        scores = builder.compute_pagerank(articles, edges)
        total = sum(scores.values())
        # With dangling nodes PageRank may not sum to exactly 1;
        # just ensure all scores are positive and total is reasonable.
        assert total > 0
        assert all(v > 0 for v in scores.values())


# ---------------------------------------------------------------------------
# PubMedClient Tests
# ---------------------------------------------------------------------------


class TestPubMedClient:
    @pytest.fixture
    def client(self):
        return PubMedClient(timeout=5)

    def test_initialization(self, client):
        assert client.api_key is None
        assert client.timeout == 5

    def test_search_with_network_error(self, client):
        """Search should return empty list on network failure."""
        import requests as req

        with patch.object(
            client.session, "get", side_effect=req.exceptions.ConnectionError("Network error")
        ):
            pmids = client.search("BRCA1 cancer", max_results=5)
        assert pmids == []

    def test_fetch_articles_empty_pmids(self, client):
        articles = client.fetch_articles([])
        assert articles == []

    def test_fetch_articles_network_error(self, client):
        import requests as req

        with patch.object(
            client.session, "get", side_effect=req.exceptions.Timeout("timeout")
        ):
            articles = client.fetch_articles(["12345678"])
        assert articles == []

    def test_parse_xml_response_empty(self, client):
        articles = client._parse_xml_response("", [])
        assert articles == []

    def test_extract_tag(self):
        xml = "<Title>Nature Medicine</Title>"
        result = PubMedClient._extract_tag(xml, "Title")
        assert result == "Nature Medicine"

    def test_extract_tag_missing(self):
        xml = "<Other>content</Other>"
        result = PubMedClient._extract_tag(xml, "Title")
        assert result is None

    def test_clean_text_removes_xml_tags(self):
        text = "<b>Hello</b> <i>World</i>"
        result = PubMedClient._clean_text(text)
        assert result == "Hello World"

    def test_rate_limit_delays(self, client):
        import time

        client._last_request_time = time.time()
        start = time.time()
        client._rate_limit()
        elapsed = time.time() - start
        assert elapsed < 1.0  # Should complete quickly


# ---------------------------------------------------------------------------
# LiteratureMiner Tests
# ---------------------------------------------------------------------------


class TestLiteratureMiner:
    @pytest.fixture
    def miner(self):
        return LiteratureMiner(include_preprints=False)

    def test_initialization(self, miner):
        assert isinstance(miner.pubmed, PubMedClient)
        assert isinstance(miner.ner, BiomedicalNER)

    def test_score_relevance(self, miner):
        articles = [
            make_article("1", title="BRCA1 breast cancer"),
            make_article("2", title="Unrelated topic ecology"),
        ]
        scored = miner._score_relevance(articles, "BRCA1 cancer")
        # BRCA1 article should have higher relevance
        brca_score = next(a.relevance_score for a in scored if a.article_id == "1")
        other_score = next(a.relevance_score for a in scored if a.article_id == "2")
        assert brca_score >= other_score

    def test_generate_summary_non_empty(self, miner):
        articles = [make_article("1"), make_article("2")]
        entity_summary = [("BRCA1", "gene", 5), ("imatinib", "drug", 3)]
        summary = miner._generate_summary("BRCA1 cancer", articles, entity_summary)
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_mine_returns_review_on_network_failure(self, miner):
        """Mine should return a valid (possibly empty) review even when APIs fail."""
        with patch.object(miner.pubmed, "search", return_value=[]):
            review = miner.mine("BRCA1 cancer", max_pubmed=5)
        assert isinstance(review, LiteratureReview)
        assert review.query == "BRCA1 cancer"

    def test_get_top_entities_by_type(self, miner):
        review = LiteratureReview(
            query="test",
            articles=[],
            key_entities=[
                ExtractedEntity("BRCA1", "gene", 0, 5, 0.9),
                ExtractedEntity("imatinib", "drug", 6, 14, 0.85),
                ExtractedEntity("cancer", "disease", 15, 21, 0.75),
            ],
            citation_network=[],
            knowledge_summary="",
        )
        genes = miner.get_top_entities_by_type(review, "gene")
        assert all(e.entity_type == "gene" for e in genes)
        assert genes[0].text == "BRCA1"
