-- KPIs do funil em SQL (DuckDB lê o CSV diretamente)
-- Uso: duckdb -c ".read sql/kpis.sql"

CREATE OR REPLACE VIEW deals AS
SELECT DISTINCT ON (deal_id) *
FROM read_csv_auto('data/synthetic_deals.csv');

-- 1. Taxa de ganho por canal (sobre negociações encerradas)
SELECT canal,
       COUNT(*) FILTER (WHERE status IN ('Ganho', 'Perdido'))                   AS encerradas,
       COUNT(*) FILTER (WHERE status = 'Ganho')                                 AS ganhas,
       ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'Ganho')
             / NULLIF(COUNT(*) FILTER (WHERE status IN ('Ganho', 'Perdido')), 0), 1) AS taxa_ganho_pct
FROM deals
GROUP BY canal
ORDER BY taxa_ganho_pct DESC;

-- 2. Ciclo de venda (dias) — mediana e P90 por segmento
SELECT segmento,
       MEDIAN(date_diff('day', criado_em, fechado_em))              AS ciclo_mediano,
       QUANTILE_CONT(date_diff('day', criado_em, fechado_em), 0.9)  AS ciclo_p90
FROM deals
WHERE status = 'Ganho' AND fechado_em >= criado_em
GROUP BY segmento;

-- 3. Teste de controle: vendas ganhas sem contrato assinado
SELECT deal_id, canal, distribuidora, fechado_em
FROM deals
WHERE status = 'Ganho' AND contrato_assinado <> 'Sim';
