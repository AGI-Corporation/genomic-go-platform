-- Genomic.go Platform - PostgreSQL Schema
-- Stores core genomic entities and experiment records.

-- Genes
CREATE TABLE IF NOT EXISTS genes (
    gene_id       SERIAL PRIMARY KEY,
    symbol        VARCHAR(50)  NOT NULL,
    name          TEXT         NOT NULL,
    chromosome    VARCHAR(10),
    start_pos     BIGINT,
    end_pos       BIGINT,
    strand        CHAR(1)      CHECK (strand IN ('+', '-')),
    organism      VARCHAR(100) NOT NULL DEFAULT 'Homo sapiens',
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_genes_symbol ON genes (symbol);
CREATE INDEX IF NOT EXISTS idx_genes_chromosome ON genes (chromosome);

-- Variants
CREATE TABLE IF NOT EXISTS variants (
    variant_id            SERIAL PRIMARY KEY,
    gene_id               INTEGER REFERENCES genes (gene_id) ON DELETE SET NULL,
    rsid                  VARCHAR(20),
    chromosome            VARCHAR(10),
    position              BIGINT,
    ref_allele            TEXT,
    alt_allele            TEXT,
    clinical_significance VARCHAR(100),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_variants_gene_id   ON variants (gene_id);
CREATE INDEX IF NOT EXISTS idx_variants_rsid      ON variants (rsid);
CREATE INDEX IF NOT EXISTS idx_variants_chromosome_pos ON variants (chromosome, position);

-- Proteins
CREATE TABLE IF NOT EXISTS proteins (
    protein_id       SERIAL PRIMARY KEY,
    gene_id          INTEGER REFERENCES genes (gene_id) ON DELETE SET NULL,
    uniprot_id       VARCHAR(20) UNIQUE,
    name             TEXT NOT NULL,
    sequence         TEXT,
    molecular_weight NUMERIC(12, 2),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_proteins_gene_id    ON proteins (gene_id);
CREATE INDEX IF NOT EXISTS idx_proteins_uniprot_id ON proteins (uniprot_id);

-- Pathways
CREATE TABLE IF NOT EXISTS pathways (
    pathway_id  SERIAL PRIMARY KEY,
    name        TEXT        NOT NULL,
    source      VARCHAR(50) NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pathways_source ON pathways (source);

-- Gene-Pathway join table
CREATE TABLE IF NOT EXISTS gene_pathways (
    gene_id    INTEGER NOT NULL REFERENCES genes (gene_id) ON DELETE CASCADE,
    pathway_id INTEGER NOT NULL REFERENCES pathways (pathway_id) ON DELETE CASCADE,
    PRIMARY KEY (gene_id, pathway_id)
);

-- Experiments
CREATE TABLE IF NOT EXISTS experiments (
    experiment_id UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id      TEXT        NOT NULL,
    type          VARCHAR(100) NOT NULL,
    input_data    JSONB,
    output_data   JSONB,
    status        VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_experiments_agent_id ON experiments (agent_id);
CREATE INDEX IF NOT EXISTS idx_experiments_status   ON experiments (status);
CREATE INDEX IF NOT EXISTS idx_experiments_type     ON experiments (type);
