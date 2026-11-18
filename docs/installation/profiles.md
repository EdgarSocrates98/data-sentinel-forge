# Profiles de instalação

| Profile | Conteúdo |
|---|---|
| `minimal` | marker + MCP; sem skills/agents |
| `recommended` | marker + MCP + skills + agents (padrão) |
| `full` | **idêntico ao `recommended`** — equivalência declarada |

```bash
data-sentinel install --profile full --yes
```

**`full ≡ recommended` (equivalência honesta):** o Data Sentinel não tem
componentes de catálogo além do conjunto recommended — os `asset_kinds`
dos dois profiles são os mesmos por construção. Declaramos a
equivalência em vez de fingir diferenciação (regra §5.4 dos perfis): se
o pacote um dia ganhar componentes adicionais homologados, `full` passa
a tê-los e esta nota sai.

O profile só controla *que tipos* de asset são planejados — os writes
sempre passam pelo ledger. `--components skills,agents` faz override
fino. O perfil de gateway (`--gateway-profile economy|balanced|deep`;
`--gateway` é o alias legado) é advisory — registrado no receipt, nunca
altera limites de segurança.
