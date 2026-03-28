"""Tests for the compound library semantic search module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from compound_library.compound_searcher import CompoundSearcher


@pytest.fixture
def mock_qdrant_client():
    """Return a fresh Mock to use as the QdrantClient instance."""
    return Mock()


@pytest.fixture
def searcher(mock_qdrant_client):
    """Create CompoundSearcher with a mocked QdrantClient."""
    with patch("compound_library.compound_searcher.QdrantClient") as MockClient:
        MockClient.return_value = mock_qdrant_client
        instance = CompoundSearcher(
            collection_name="test_compounds",
            qdrant_url="http://localhost:6333",
            qdrant_api_key=None,
        )
    return instance


class TestCompoundSearcherInit:
    """Tests for CompoundSearcher initialization."""

    def test_stores_collection_name(self, searcher):
        assert searcher.collection_name == "test_compounds"

    def test_stores_embeddings_model(self, searcher):
        assert searcher.embeddings_model == "sentence-transformers/all-MiniLM-L6-v2"

    def test_custom_embeddings_model(self, mock_qdrant_client):
        """Test that a custom embeddings model is stored."""
        with patch("compound_library.compound_searcher.QdrantClient"):
            s = CompoundSearcher(
                collection_name="compounds",
                qdrant_url="http://localhost:6333",
                embeddings_model="custom-model",
            )
        assert s.embeddings_model == "custom-model"


class TestCompoundSearcherSearch:
    """Tests for the search method."""

    def _make_hit(self, payload, score=None):
        """Create a mock search hit."""
        if score is not None:
            hit = Mock(spec=["payload", "score"])
            hit.score = score
        else:
            hit = Mock(spec=["payload"])
        hit.payload = payload
        return hit

    def test_search_returns_results(self, searcher, mock_qdrant_client):
        """Test that search returns compound data from Qdrant."""
        hit = self._make_hit({"name": "Imatinib", "mechanism": "Kinase inhibitor"}, score=0.92)
        mock_qdrant_client.query_points.return_value = Mock(points=[hit])

        results = searcher.search("kinase inhibitor")

        assert len(results) == 1
        assert results[0]["name"] == "Imatinib"
        assert results[0]["similarity_score"] == 0.92

    def test_search_attaches_none_score_when_missing(self, searcher, mock_qdrant_client):
        """Test that similarity_score is None when the hit has no score attribute."""
        hit = Mock(spec=["payload"])
        hit.payload = {"name": "Mystery Drug"}
        mock_qdrant_client.query_points.return_value = Mock(points=[hit])

        results = searcher.search("mystery")

        assert results[0]["similarity_score"] is None

    def test_search_empty_results(self, searcher, mock_qdrant_client):
        """Test that an empty Qdrant result produces an empty list."""
        mock_qdrant_client.query_points.return_value = Mock(points=[])

        results = searcher.search("nonexistent compound")

        assert results == []

    def test_search_no_filters_passes_none_filter(self, searcher, mock_qdrant_client):
        """Test that search without filters passes query_filter=None."""
        mock_qdrant_client.query_points.return_value = Mock(points=[])

        searcher.search("query")

        call_kwargs = mock_qdrant_client.query_points.call_args
        assert call_kwargs.kwargs.get("query_filter") is None

    def test_search_with_filters_builds_filter(self, searcher, mock_qdrant_client):
        """Test that search with filters passes a non-None filter object."""
        mock_qdrant_client.query_points.return_value = Mock(points=[])

        searcher.search("cancer drug", filters={"therapeutic_area": "oncology"}, limit=5)

        call_kwargs = mock_qdrant_client.query_points.call_args
        assert call_kwargs.kwargs.get("query_filter") is not None
        assert call_kwargs.kwargs.get("limit") == 5

    def test_search_respects_limit(self, searcher, mock_qdrant_client):
        """Test that the limit parameter is forwarded to Qdrant."""
        mock_qdrant_client.query_points.return_value = Mock(points=[])

        searcher.search("query", limit=3)

        call_kwargs = mock_qdrant_client.query_points.call_args
        assert call_kwargs.kwargs.get("limit") == 3

    def test_search_does_not_mutate_payload(self, searcher, mock_qdrant_client):
        """Test that the original payload dict is not mutated."""
        original = {"name": "Drug A"}
        hit = self._make_hit(original, score=0.8)
        mock_qdrant_client.query_points.return_value = Mock(points=[hit])

        results = searcher.search("Drug A")

        # similarity_score should be added to the copy, not the original
        assert "similarity_score" not in original
        assert "similarity_score" in results[0]


class TestCompoundSearcherBuildFilter:
    """Tests for the _build_filter helper."""

    def test_build_filter_empty_returns_none(self, searcher):
        result = searcher._build_filter({})
        assert result is None

    def test_build_filter_molecular_weight_range(self, searcher):
        result = searcher._build_filter({"molecular_weight_range": [200, 500]})
        assert result is not None
        keys = [c.key for c in result.must]
        assert "molecular_weight" in keys

    def test_build_filter_target_protein(self, searcher):
        result = searcher._build_filter({"target_protein": "EGFR"})
        assert result is not None
        cond = result.must[0]
        assert cond.key == "target_protein"
        assert cond.match.value == "EGFR"

    def test_build_filter_mechanism(self, searcher):
        result = searcher._build_filter({"mechanism": "kinase inhibitor"})
        assert result is not None
        cond = result.must[0]
        assert cond.key == "mechanism"
        assert cond.match.value == "kinase inhibitor"

    def test_build_filter_therapeutic_area(self, searcher):
        result = searcher._build_filter({"therapeutic_area": "oncology"})
        assert result is not None
        cond = result.must[0]
        assert cond.key == "therapeutic_area"
        assert cond.match.value == "oncology"

    def test_build_filter_multiple_conditions(self, searcher):
        result = searcher._build_filter(
            {
                "therapeutic_area": "oncology",
                "target_protein": "EGFR",
                "molecular_weight_range": [200, 600],
            }
        )
        assert result is not None
        assert len(result.must) == 3

    def test_build_filter_unknown_key_ignored(self, searcher):
        """Only known filter keys produce conditions; unknown keys are ignored."""
        result = searcher._build_filter({"unknown_key": "value"})
        assert result is None


class TestCompoundSearcherFindSimilar:
    """Tests for find_similar_compounds."""

    def test_find_similar_compounds_raises_when_not_found(self, searcher, mock_qdrant_client):
        mock_qdrant_client.retrieve.return_value = []

        with pytest.raises(ValueError, match="Compound missing_id not found"):
            searcher.find_similar_compounds("missing_id")

    def test_find_similar_compounds_excludes_self(self, searcher, mock_qdrant_client):
        """Test the reference compound itself is excluded from results."""
        ref = Mock()
        ref.vector = [0.0] * 384
        mock_qdrant_client.retrieve.return_value = [ref]

        self_hit = Mock()
        self_hit.id = "compound_001"
        self_hit.payload = {"name": "Self"}
        self_hit.score = 1.0
        mock_qdrant_client.search.return_value = [self_hit]

        results = searcher.find_similar_compounds("compound_001")
        assert results == []

    def test_find_similar_compounds_returns_others(self, searcher, mock_qdrant_client):
        """Test that non-self results are returned with similarity scores."""
        ref = Mock()
        ref.vector = [0.1] * 384
        mock_qdrant_client.retrieve.return_value = [ref]

        self_hit = Mock()
        self_hit.id = "compound_001"
        self_hit.payload = {"name": "Self"}
        self_hit.score = 1.0

        similar_hit = Mock()
        similar_hit.id = "compound_002"
        similar_hit.payload = {"name": "Similar Drug"}
        similar_hit.score = 0.85

        mock_qdrant_client.search.return_value = [self_hit, similar_hit]

        results = searcher.find_similar_compounds("compound_001", limit=10)
        assert len(results) == 1
        assert results[0]["name"] == "Similar Drug"
        assert results[0]["similarity_score"] == 0.85

    def test_find_similar_compounds_respects_limit(self, searcher, mock_qdrant_client):
        """Test that only `limit` results are returned."""
        ref = Mock()
        ref.vector = [0.1] * 10
        mock_qdrant_client.retrieve.return_value = [ref]

        hits = []
        for i in range(10):
            h = Mock()
            h.id = f"c_{i}"
            h.payload = {"name": f"Drug {i}"}
            h.score = 0.9 - i * 0.01
            hits.append(h)
        mock_qdrant_client.search.return_value = hits

        results = searcher.find_similar_compounds("compound_001", limit=3)
        assert len(results) == 3


class TestCompoundSearcherCollectionStats:
    """Tests for get_collection_stats."""

    def test_get_collection_stats_returns_correct_fields(self, searcher, mock_qdrant_client):
        info = Mock()
        info.points_count = 500
        info.config.params.vectors.size = 384
        info.config.params.vectors.distance = "Cosine"
        info.status = "green"
        mock_qdrant_client.get_collection.return_value = info

        stats = searcher.get_collection_stats()

        assert stats["total_compounds"] == 500
        assert stats["vector_size"] == 384
        assert stats["distance_metric"] == "Cosine"
        assert stats["status"] == "green"

    def test_get_collection_stats_calls_correct_collection(self, searcher, mock_qdrant_client):
        info = Mock()
        info.points_count = 0
        info.config.params.vectors.size = 0
        info.config.params.vectors.distance = "Dot"
        info.status = "yellow"
        mock_qdrant_client.get_collection.return_value = info

        searcher.get_collection_stats()
        mock_qdrant_client.get_collection.assert_called_once_with(
            collection_name="test_compounds"
        )
