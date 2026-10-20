# Interoperabilidade com Forge Doctor

## O que é

O Sentinel importa saídas do Forge Doctor (data e api) como findings com
proveniência externa — sem exigir o Doctor instalado, sem executar
conteúdo do bundle e sem rede.

## Formatos aceitos

| Formato | Como produzir | Detecção |
|---|---|---|
| handoff-bundle@1 | `forge-doctor-data export --format handoff` | `contract:"handoff-bundle"` + `results` |
| forge-contracts/1 | fixtures/contratos compartilhados | `contract_version:"forge-contracts/1"` + `findings` |
| scan-json@3.0 | `forge-doctor-data scan --format json` | `schema_version:"3.0"` + `results` |

## Uso

```bash
forge-doctor-data export --format handoff . > handoff.json
data-sentinel import doctor-bundle -f handoff.json
data-sentinel import doctor-bundle -f handoff.json --json
```

## Semântica de importação

- Todo finding importado vira `Finding` interno com prefixo
  `[importado:<producer>]` e preserva `check_id`/`fingerprint`.
- Evidência associada é `provenance=declared` com `source=<producer:versão>`.
- Confiança → status: high→PROBABLE, medium/low→POSSIBLE,
  ausente/unknown→UNKNOWN. **Nunca CONFIRMED** — um bundle externo é uma
  declaração, não uma observação do Sentinel.
- `unknowns` do produtor são preservados e contados na explicação.
- Segredos são redigidos em mensagens, evidence e locations.

## Limites de segurança

- Arquivo ≤ 20 MB; findings truncados em 10.000 com limitação declarada.
- JSON apenas — nenhum código, expressão ou caminho do bundle é executado
  ou seguido (`file://`, `../../` são tratados como texto).
- Sem rede, sem download, sem instalação do Doctor.
