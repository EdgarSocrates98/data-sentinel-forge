# Grill Gate — Cycle 08.2

Recorded before dispatch of ds-0109..ds-0118 (prompt_evo_cycle8.2.md).

1. **Asset source**: Híbrido com fallback — assets empacotados na wheel
   (`src/data_sentinel/installation/assets/`) como fonte primária; fallback
   para diretório no checkout do repo quando rodando de source/git/zip.
   Dois modos → ambos testados.
2. **Interactive UX**: Typer+Rich existentes — zero nova dependência,
   `rich.Prompt`/`rich.Confirm`, testável via `CliRunner`.
3. **Forge CLI**: manifest machine-readable (`data-sentinel manifest`) +
   patch documentado gerado como artefato — nunca escreve no repo irmão
   sem aprovação explícita do usuário.
4. **Catalog size**: curado — 4-5 skills + 3 agents reais e testados
   (investigate, spark-plan-review, quality-drift, watch-ops, report;
   investigator, spark-specialist, reviewer). Expansível.
