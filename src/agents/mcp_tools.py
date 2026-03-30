"""Genomic.go Platform - MCP Tool Registry.

Provides a collection of tools for fetching genomic data from external
public APIs: NCBI Entrez, UniProt, PDB, ClinVar, ClinicalTrials.gov,
PubMed, and Open Targets.

All tools are plain functions that return structured dictionaries and
handle HTTP errors gracefully.
"""

import logging
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT: int = 30
_NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_UNIPROT_BASE = "https://rest.uniprot.org/uniprotkb"
_PDB_BASE = "https://data.rcsb.org/rest/v1/core/entry"
_CLINVAR_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_CLINICAL_TRIALS_BASE = "https://clinicaltrials.gov/api/v2/studies"
_PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_OPEN_TARGETS_BASE = "https://api.platform.opentargets.org/api/v4/graphql"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get(url: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
    """Perform a GET request with a default timeout.

    Args:
        url: Target URL.
        params: Optional query parameters.

    Returns:
        The :class:`requests.Response` object.

    Raises:
        requests.HTTPError: If the response status indicates an error.
    """
    response = requests.get(url, params=params, timeout=_DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def fetch_ncbi_sequence(accession: str) -> Dict[str, Any]:
    """Fetch a DNA/RNA sequence from NCBI Entrez.

    Args:
        accession: NCBI accession number (e.g. ``"NM_007294"``).

    Returns:
        Dictionary with keys ``accession``, ``sequence``, ``length``,
        and ``description``.  On error, returns a dict with ``error``.
    """
    try:
        efetch_url = f"{_NCBI_BASE}/efetch.fcgi"
        params = {
            "db": "nucleotide",
            "id": accession,
            "rettype": "fasta",
            "retmode": "text",
        }
        response = _get(efetch_url, params=params)
        lines = response.text.strip().split("\n")
        description = lines[0].lstrip(">") if lines else ""
        sequence = "".join(lines[1:])
        return {
            "accession": accession,
            "description": description,
            "sequence": sequence,
            "length": len(sequence),
        }
    except requests.RequestException as exc:
        logger.error("fetch_ncbi_sequence(%s) failed: %s", accession, exc)
        return {"accession": accession, "error": str(exc)}


def query_uniprot(protein_id: str) -> Dict[str, Any]:
    """Query UniProt for protein data.

    Args:
        protein_id: UniProt accession (e.g. ``"P04637"``).

    Returns:
        Dictionary with protein name, organism, sequence length, and
        function annotation.  On error, returns a dict with ``error``.
    """
    try:
        url = f"{_UNIPROT_BASE}/{protein_id}"
        response = requests.get(
            url,
            headers={"Accept": "application/json"},
            timeout=_DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        protein_name = (
            data.get("proteinDescription", {})
            .get("recommendedName", {})
            .get("fullName", {})
            .get("value", "Unknown")
        )
        organism = data.get("organism", {}).get("scientificName", "Unknown")
        sequence_length = data.get("sequence", {}).get("length", 0)
        function_comments = [
            c.get("texts", [{}])[0].get("value", "")
            for c in data.get("comments", [])
            if c.get("commentType") == "FUNCTION"
        ]
        return {
            "protein_id": protein_id,
            "name": protein_name,
            "organism": organism,
            "sequence_length": sequence_length,
            "function": function_comments[0] if function_comments else "",
        }
    except requests.RequestException as exc:
        logger.error("query_uniprot(%s) failed: %s", protein_id, exc)
        return {"protein_id": protein_id, "error": str(exc)}


def fetch_pdb_structure(pdb_id: str) -> Dict[str, Any]:
    """Fetch 3-D structure metadata from the RCSB PDB.

    Args:
        pdb_id: Four-character PDB identifier (e.g. ``"1TUP"``).

    Returns:
        Dictionary with title, experimental method, resolution, and
        deposition date.  On error, returns a dict with ``error``.
    """
    try:
        url = f"{_PDB_BASE}/{pdb_id.lower()}"
        response = _get(url)
        data = response.json()
        struct = data.get("struct", {})
        exptl = data.get("exptl", [{}])[0]
        reflns = data.get("reflns", [{}])[0]
        return {
            "pdb_id": pdb_id.upper(),
            "title": struct.get("title", ""),
            "experimental_method": exptl.get("method", ""),
            "resolution_angstrom": reflns.get("d_resolution_high"),
            "deposition_date": data.get("rcsb_accession_info", {}).get(
                "deposit_date", ""
            ),
        }
    except requests.RequestException as exc:
        logger.error("fetch_pdb_structure(%s) failed: %s", pdb_id, exc)
        return {"pdb_id": pdb_id, "error": str(exc)}


def classify_variant(gene: str, variant: str) -> Dict[str, Any]:
    """Get clinical significance for a variant from ClinVar.

    Args:
        gene: Gene symbol (e.g. ``"BRCA1"``).
        variant: Variant description (e.g. ``"c.5266dupC"``).

    Returns:
        Dictionary with variant details and clinical significance.
        On error, returns a dict with ``error``.
    """
    try:
        search_url = f"{_CLINVAR_BASE}/esearch.fcgi"
        query = f"{gene}[gene] AND {variant}[variant name]"
        search_params = {
            "db": "clinvar",
            "term": query,
            "retmax": 5,
            "retmode": "json",
        }
        search_response = _get(search_url, params=search_params)
        search_data = search_response.json()
        ids = search_data.get("esearchresult", {}).get("idlist", [])
        if not ids:
            return {
                "gene": gene,
                "variant": variant,
                "clinical_significance": "not_found",
                "clinvar_ids": [],
            }
        return {
            "gene": gene,
            "variant": variant,
            "clinvar_ids": ids,
            "clinical_significance": "see_clinvar",
            "query": query,
        }
    except requests.RequestException as exc:
        logger.error("classify_variant(%s, %s) failed: %s", gene, variant, exc)
        return {"gene": gene, "variant": variant, "error": str(exc)}


def search_clinical_trials(
    condition: str, phase: Optional[str] = None
) -> Dict[str, Any]:
    """Search ClinicalTrials.gov for studies matching a condition.

    Args:
        condition: Disease or condition name (e.g. ``"breast cancer"``).
        phase: Optional trial phase filter (e.g. ``"PHASE3"``).

    Returns:
        Dictionary with ``total_count`` and ``studies`` list.
        On error, returns a dict with ``error``.
    """
    try:
        params: Dict[str, Any] = {
            "query.cond": condition,
            "pageSize": 10,
            "format": "json",
        }
        if phase:
            params["filter.advanced"] = f"AREA[Phase]{phase}"
        response = _get(_CLINICAL_TRIALS_BASE, params=params)
        data = response.json()
        studies = []
        for study in data.get("studies", []):
            proto = study.get("protocolSection", {})
            id_module = proto.get("identificationModule", {})
            status_module = proto.get("statusModule", {})
            design_module = proto.get("designModule", {})
            studies.append(
                {
                    "nct_id": id_module.get("nctId", ""),
                    "title": id_module.get("briefTitle", ""),
                    "status": status_module.get("overallStatus", ""),
                    "phase": design_module.get("phases", []),
                }
            )
        return {
            "condition": condition,
            "total_count": data.get("totalCount", 0),
            "studies": studies,
        }
    except requests.RequestException as exc:
        logger.error("search_clinical_trials(%s) failed: %s", condition, exc)
        return {"condition": condition, "error": str(exc)}


def search_pubmed(query: str, max_results: int = 10) -> Dict[str, Any]:
    """Search PubMed for literature matching a query.

    Args:
        query: Free-text search query.
        max_results: Maximum number of results to return (default 10).

    Returns:
        Dictionary with ``total_count`` and ``pmids`` list.
        On error, returns a dict with ``error``.
    """
    try:
        search_url = f"{_PUBMED_BASE}/esearch.fcgi"
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
        }
        response = _get(search_url, params=params)
        data = response.json()
        result = data.get("esearchresult", {})
        return {
            "query": query,
            "total_count": int(result.get("count", 0)),
            "pmids": result.get("idlist", []),
        }
    except requests.RequestException as exc:
        logger.error("search_pubmed(%r) failed: %s", query, exc)
        return {"query": query, "error": str(exc)}


def query_open_targets(target_id: str) -> Dict[str, Any]:
    """Query Open Targets Platform for drug-target associations.

    Uses the Open Targets GraphQL API.

    Args:
        target_id: Ensembl gene identifier (e.g. ``"ENSG00000141510"``).

    Returns:
        Dictionary with gene symbol, approved name, and known drugs.
        On error, returns a dict with ``error``.
    """
    try:
        gql_query = """
        query TargetAssociations($ensemblId: String!) {
          target(ensemblId: $ensemblId) {
            id
            approvedSymbol
            approvedName
            knownDrugs {
              count
              rows {
                drug { name }
                phase
                status
              }
            }
          }
        }
        """
        payload = {"query": gql_query, "variables": {"ensemblId": target_id}}
        response = requests.post(
            _OPEN_TARGETS_BASE,
            json=payload,
            timeout=_DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json().get("data", {}).get("target", {})
        known_drugs = data.get("knownDrugs", {})
        return {
            "target_id": target_id,
            "symbol": data.get("approvedSymbol", ""),
            "name": data.get("approvedName", ""),
            "known_drug_count": known_drugs.get("count", 0),
            "drugs": [
                {
                    "name": row.get("drug", {}).get("name", ""),
                    "phase": row.get("phase"),
                    "status": row.get("status", ""),
                }
                for row in known_drugs.get("rows", [])[:10]
            ],
        }
    except requests.RequestException as exc:
        logger.error("query_open_targets(%s) failed: %s", target_id, exc)
        return {"target_id": target_id, "error": str(exc)}


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

TOOL_REGISTRY: Dict[str, Any] = {
    "fetch_ncbi_sequence": fetch_ncbi_sequence,
    "query_uniprot": query_uniprot,
    "fetch_pdb_structure": fetch_pdb_structure,
    "classify_variant": classify_variant,
    "search_clinical_trials": search_clinical_trials,
    "search_pubmed": search_pubmed,
    "query_open_targets": query_open_targets,
}
