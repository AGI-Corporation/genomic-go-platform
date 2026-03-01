"""Biological Data Parsers for Genomic.go

Utilities for parsing common genomic formats (VCF, FASTA)
into structured formats for agent analysis.
"""

from typing import List, Dict, Any

def parse_vcf(filepath: str) -> List[Dict[str, Any]]:
    """Simple parser for VCF files, extracting key variants."""
    variants = []
    with open(filepath, 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) >= 5:
                variants.append({
                    "chrom": parts[0],
                    "pos": parts[1],
                    "id": parts[2],
                    "ref": parts[3],
                    "alt": parts[4],
                    "qual": parts[5] if len(parts) > 5 else "N/A"
                })
    return variants

def parse_fasta(filepath: str) -> Dict[str, str]:
    """Simple parser for FASTA files, extracting sequences by header."""
    sequences = {}
    current_header = None
    current_seq = []

    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('>'):
                if current_header:
                    sequences[current_header] = "".join(current_seq)
                current_header = line[1:]
                current_seq = []
            else:
                current_seq.append(line)

        if current_header:
            sequences[current_header] = "".join(current_seq)

    return sequences

if __name__ == "__main__":
    # Test parsers
    print("VCF Parsing Test:")
    print(parse_vcf("data/sample/patient_001.vcf"))
    print("\nFASTA Parsing Test:")
    print(parse_fasta("data/sample/target_sequence.fasta"))
