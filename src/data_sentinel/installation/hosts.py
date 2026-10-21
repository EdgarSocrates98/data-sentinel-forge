"""Mapa de renderização por host — os diretórios que cada AI Host lê.

Verdade portada das forjas irmãs: ``sparkforge_aws/install/hosts.py``
(escopo ``project``/``workspace``) e ``sparkforge_aws/integrate/hosts.py``
(escopo ``user``), confirmada contra a tabela ``_host_dirs`` do installkit
vendado. Nenhum layout foi inventado aqui.

- ``claude``  — ``.claude/skills/<n>/SKILL.md`` + ``.claude/agents/<n>.md``,
  ambos byte-idênticos (o host não lê campos extras).
- ``devin``   — ``.devin/{skills,agents}`` mais o espelho compartilhado
  ``.agents/{skills,agents}`` que o Devin lê nativamente. Nos agents o
  campo ``tools:`` sai do frontmatter: o Devin aceita a chave, mas o
  mapeamento de valores não é documentado — omitir herda o default
  permissivo do harness, que é o comportamento documentado.
- ``codex``   — ``.agents/skills`` (a superfície compartilhada, com a
  renderização ``devin``) + ``.codex/agents/<n>.toml`` com chaves de topo
  ``name``/``description``/``developer_instructions``.
- ``copilot`` — ``.github/skills/<n>/SKILL.md`` (renderização ``devin``) +
  ``.github/agents/<n>.agent.md`` (byte-idêntico).
- ``cursor``  — **sem adapter homologado**: a auditoria de paridade do
  ciclo 08.2 registra que nenhuma forja irmã publica assets para Cursor,
  então ``cursor`` não rende espelho nenhum aqui. O que ele recebe de
  fato no install é o marcador gerenciado em ``AGENTS.md`` (que o Cursor
  lê nativamente) e o ``.mcp.json`` compartilhado do kit — declarar mais
  que isso seria suporte fingido.

Escopo ``workspace`` usa o mesmo mapa de ``project`` (a raiz é a do
workspace). Escopo ``user`` usa os diretórios de usuário dos siblings:
``~/.agents/skills`` compartilhado, ``~/.config/devin`` (ou
``%APPDATA%\\devin`` no Windows), ``~/.codex``, ``~/.copilot`` e
``~/.claude``.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class HostLayout:
    """Onde um host lê skills e agents, relativo à raiz do escopo."""

    skill_dirs: tuple[str, ...]
    skill_platform: str  # "claude" (passthrough) | "devin" (subagent/agent)
    agent_dirs: tuple[str, ...]
    agent_pattern: str  # "{stem}.md" | "{stem}.toml" | "{stem}.agent.md"
    agent_platform: str  # "claude" | "devin" | "codex" | "github"


PROJECT_LAYOUTS: dict[str, HostLayout] = {
    "claude": HostLayout(
        skill_dirs=(".claude/skills",),
        skill_platform="claude",
        agent_dirs=(".claude/agents",),
        agent_pattern="{stem}.md",
        agent_platform="claude",
    ),
    "devin": HostLayout(
        skill_dirs=(".devin/skills", ".agents/skills"),
        skill_platform="devin",
        agent_dirs=(".devin/agents", ".agents/agents"),
        agent_pattern="{stem}.md",
        agent_platform="devin",
    ),
    "codex": HostLayout(
        skill_dirs=(".agents/skills",),
        skill_platform="devin",
        agent_dirs=(".codex/agents",),
        agent_pattern="{stem}.toml",
        agent_platform="codex",
    ),
    "copilot": HostLayout(
        skill_dirs=(".github/skills",),
        skill_platform="devin",
        agent_dirs=(".github/agents",),
        agent_pattern="{stem}.agent.md",
        agent_platform="github",
    ),
}


def _devin_user_agents() -> str:
    """``~/.config/devin/agents``; ``%APPDATA%\\devin\\agents`` no Windows."""
    return "AppData/Roaming/devin/agents" if os.name == "nt" else ".config/devin/agents"


USER_LAYOUTS: dict[str, HostLayout] = {
    "claude": HostLayout(
        skill_dirs=(".claude/skills",),
        skill_platform="claude",
        agent_dirs=(".claude/agents",),
        agent_pattern="{stem}.md",
        agent_platform="claude",
    ),
    "devin": HostLayout(
        skill_dirs=(".agents/skills",),
        skill_platform="devin",
        agent_dirs=(_devin_user_agents(),),
        agent_pattern="{stem}.md",
        agent_platform="devin",
    ),
    "codex": HostLayout(
        skill_dirs=(".agents/skills",),
        skill_platform="devin",
        agent_dirs=(".codex/agents",),
        agent_pattern="{stem}.toml",
        agent_platform="codex",
    ),
    "copilot": HostLayout(
        skill_dirs=(".agents/skills",),
        skill_platform="devin",
        agent_dirs=(".copilot/agents",),
        agent_pattern="{stem}.agent.md",
        agent_platform="github",
    ),
}

# Hosts declarados em service.HOSTS sem adapter de assets homologado:
# rendem nada aqui e a razão fica escrita — suporte fingido é pior que
# suporte ausente.
UNSUPPORTED_HOSTS: dict[str, str] = {
    "cursor": (
        "nenhuma forja irmã publica assets de skills/agents para Cursor; "
        "o que o host recebe no install é o marcador AGENTS.md (lido "
        "nativamente) e o .mcp.json gerenciado do kit"
    ),
}

# Despacho Devin (`subagent:`/`agent:` no espelho `.agents/skills`):
# despacha quem é investigação fechada sobre artefato — não pergunta nada
# a ninguém. Toda skill do catálogo precisa de decisão registrada aqui,
# com a razão ao lado; o default silencioso seria publicar sem ninguém ter
# decidido se ela roda sem poder perguntar.
DISPATCHABLE_SKILLS: dict[str, str] = {
    "data-sentinel-spark-plan": (
        "lê um plano/log já salvo e devolve findings; leitura fechada"
    ),
    "data-sentinel-sql-review": (
        "análise estática de um .sql fechado; a saída é relatório"
    ),
    "data-sentinel-quality-drift": (
        "valida contrato e normaliza exports já em disco; leitura fechada"
    ),
    "data-sentinel-report": (
        "renderiza relatório persistido/exportado; não decide nada"
    ),
}
NON_DISPATCHABLE_SKILLS: dict[str, str] = {
    "data-sentinel-investigate": (
        "roteia especialistas e decide quais verbos correm — a orquestração "
        "fica no agente pai; subagente não gera subagente por default"
    ),
}
SKILL_DISPATCH_REASON = {**DISPATCHABLE_SKILLS, **NON_DISPATCHABLE_SKILLS}

# Perfis que dirigem o loop — nunca destino `agent:` de skill despachável.
ORCHESTRATOR_PROFILES: frozenset[str] = frozenset({"sentinel-investigator"})

# Perfis embutidos do Devin — colisão de `name:` é proibida pela fonte e
# o comportamento resultante não é documentado: recusar é a leitura segura.
DEVIN_BUILTIN_PROFILE_NAMES: frozenset[str] = frozenset(
    {"subagent_explore", "subagent_general"}
)

DEVIN_DROPPED_AGENT_KEYS: frozenset[str] = frozenset({"tools"})
DEVIN_SKILL_DISPATCH_KEYS: frozenset[str] = frozenset({"subagent", "agent"})

AGENT_PLATFORMS: frozenset[str] = frozenset(
    {"claude", "github", "devin", "codex"}
)


@dataclass(frozen=True)
class AssetCatalog:
    """O catálogo canônico já lido de ``installation/assets/``.

    ``skills[name][inner]`` guarda cada arquivo da skill (``SKILL.md`` e
    anexos); ``agents[stem]`` guarda o markdown do perfil; ``overlays``
    guarda ``hosts/<host>/<rel>`` — arquivos específicos de um host,
    emitidos sem transformação; ``manifest`` fica fora do render (o
    ``forge.json`` é descoberta do Sentinel, não asset de projeto).
    """

    skills: dict[str, dict[str, bytes]]
    agents: dict[str, bytes]
    overlays: dict[str, dict[str, bytes]]
    manifest: dict[str, bytes]


# ---------------------------------------------------------------------------
# Frontmatter — leitura por linha, sem round-trip de YAML
# ---------------------------------------------------------------------------

_FENCE = "---"
_TOP_LEVEL_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_.-]*)\s*:")
_LIST_ITEM = re.compile(r"^\s*-\s+(.*)$")


def split_frontmatter(text: str) -> tuple[list[str], list[str], list[str]] | None:
    """Fatia em (cerca de abertura, corpo do frontmatter, resto).

    Linhas com fim de linha preservado — renderização compara byte a byte
    e normalizar CRLF produziria divergência numa árvore com ``autocrlf``.
    ``None`` quando não há frontmatter delimitado.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != _FENCE:
        return None
    for index, line in enumerate(lines[1:], start=1):
        if line.rstrip("\r\n") == _FENCE:
            return lines[:1], lines[1:index], lines[index:]
    return None


def _drop_frontmatter_keys(front: list[str], keys: frozenset[str]) -> list[str]:
    """Remove chaves de topo do frontmatter, com as continuações delas."""
    kept: list[str] = []
    dropping = False
    for line in front:
        content = line.rstrip("\r\n")
        if content[:1] in (" ", "\t"):
            if not dropping:
                kept.append(line)
            continue
        match = _TOP_LEVEL_KEY.match(content)
        dropping = match is not None and match.group(1) in keys
        if not dropping:
            kept.append(line)
    return kept


def _valor_escalar(key: str, bruto: str, continua: bool) -> str | None:
    """Escalar de linha única; o que a leitura por linha não lê é recusado."""
    if re.match(r"^[|>][-+0-9]*$", bruto):
        raise ValueError(f"escalar_yaml_nao_suportado: `{key}` em bloco ({bruto!r})")
    if continua:
        raise ValueError(f"escalar_yaml_nao_suportado: `{key}` continua na linha de baixo")
    if bruto[:1] == '"':
        if len(bruto) < 2 or not bruto.endswith('"') or "\\" in bruto:
            raise ValueError(
                f"escalar_yaml_nao_suportado: `{key}` entre aspas duplas com escape"
            )
        return bruto[1:-1] or None
    if bruto[:1] == "'":
        miolo = bruto[1:-1]
        if len(bruto) < 2 or not bruto.endswith("'") or "'" in miolo.replace("''", ""):
            raise ValueError(
                f"escalar_yaml_nao_suportado: `{key}` entre aspas simples mal fechadas"
            )
        return miolo.replace("''", "'") or None
    return bruto or None


def frontmatter_scalar(front: list[str], key: str) -> str | None:
    """Um escalar de topo do frontmatter, ou ``None`` se ausente."""
    for index, line in enumerate(front):
        content = line.rstrip("\r\n")
        if content[:1] in (" ", "\t"):
            continue
        match = _TOP_LEVEL_KEY.match(content)
        if match and match.group(1) == key:
            bruto = content.split(":", 1)[1].strip()
            seguinte = front[index + 1].rstrip("\r\n") if index + 1 < len(front) else ""
            continua = (
                bool(bruto) and seguinte[:1] in (" ", "\t") and bool(seguinte.strip())
            )
            return _valor_escalar(key, bruto, continua)
    return None


def _frontmatter_list(front: list[str], key: str) -> list[str]:
    """Lista de topo nas duas formas do corpus (bloco e ``[a, b]``)."""
    values: list[str] = []
    collecting = False
    for line in front:
        content = line.rstrip("\r\n")
        if content[:1] in (" ", "\t"):
            if collecting:
                item = _LIST_ITEM.match(content)
                if item:
                    values.append(item.group(1).strip().strip("'\""))
            continue
        match = _TOP_LEVEL_KEY.match(content)
        collecting = False
        if match and match.group(1) == key:
            inline = content.split(":", 1)[1].strip()
            if not inline:
                collecting = True
            elif inline.startswith("[") and inline.endswith("]"):
                values.extend(
                    part.strip().strip("'\"")
                    for part in inline[1:-1].split(",")
                    if part.strip()
                )
            else:
                values.append(inline.strip("'\""))
    return values


def _newline_of(lines: list[str]) -> str:
    """O fim de linha do arquivo, para a linha inserida usar o mesmo."""
    for line in reversed(lines):
        if line.endswith("\r\n"):
            return "\r\n"
        if line.endswith("\n"):
            return "\n"
    return "\n"


# ---------------------------------------------------------------------------
# Renderização por plataforma
# ---------------------------------------------------------------------------


def _declared_skills(agent_text: str) -> tuple[str, ...]:
    """O ``skills:`` do frontmatter de um perfil, ou vazio."""
    parsed = split_frontmatter(agent_text)
    if parsed is None:
        return ()
    return tuple(_frontmatter_list(parsed[1], "skills"))


def _declarants(agents: dict[str, bytes]) -> dict[str, list[str]]:
    """skill -> perfis que a declaram, derivado do frontmatter de cada um."""
    relation: dict[str, list[str]] = {}
    for stem, data in agents.items():
        for skill in _declared_skills(data.decode("utf-8")):
            relation.setdefault(skill, []).append(stem)
    return {skill: sorted(stems) for skill, stems in sorted(relation.items())}


def _agent_for_skill(
    name: str, declarants: dict[str, list[str]]
) -> str | None:
    """O ``agent:`` da skill, ou ``None`` quando o Devin deve escolher.

    Skill declarada por mais de um perfil não nomeia ``agent:`` — ordem
    alfabética não é critério de competência. Declarante único que é
    orquestrador também não: despachar para quem dirige o loop é publicar
    propriedade mecânica com cara de decisão.
    """
    stems = declarants.get(name, [])
    if len(stems) != 1 or stems[0] in ORCHESTRATOR_PROFILES:
        return None
    return stems[0]


def render_agent(text: str, platform: str) -> str:
    """O perfil no formato que ``platform`` lê.

    ``claude``/``github`` recebem byte a byte; ``devin`` perde ``tools:``
    do frontmatter; ``codex`` vira TOML de ``~/.codex/agents/``.
    """
    if platform not in AGENT_PLATFORMS:
        raise ValueError(
            f"plataforma desconhecida: {platform!r}; "
            f"conhecidas: {sorted(AGENT_PLATFORMS)}"
        )
    if platform in ("claude", "github"):
        return text
    if platform == "codex":
        return _codex_toml(text)
    parsed = split_frontmatter(text)
    if parsed is None:
        return text
    opening, front, rest = parsed
    kept = _drop_frontmatter_keys(front, DEVIN_DROPPED_AGENT_KEYS)
    if kept == front:
        return text
    return "".join(opening + kept + rest)


def render_skill(
    text: str,
    platform: str,
    *,
    name: str,
    agent: str | None,
) -> str:
    """A ``SKILL.md`` no formato que ``platform`` lê.

    ``claude`` recebe byte a byte. ``devin`` (a superfície ``.agents/`` e
    ``.devin/``/``.github/``) recebe ``subagent: true`` e ``agent:`` nas
    skills despacháveis — campos inseridos no fim do frontmatter,
    imediatamente antes da cerca de fechamento.
    """
    if platform not in ("claude", "github", "devin", "codex"):
        raise ValueError(f"plataforma de skill desconhecida: {platform!r}")
    if name not in SKILL_DISPATCH_REASON:
        raise ValueError(
            f"skill sem decisão de despacho registrada: {name!r}. Declare "
            "em DISPATCHABLE_SKILLS ou NON_DISPATCHABLE_SKILLS com a razão "
            "ao lado."
        )
    if platform != "devin":
        return text
    parsed = split_frontmatter(text)
    if parsed is None:
        return text
    opening, front, rest = parsed
    kept = _drop_frontmatter_keys(front, DEVIN_SKILL_DISPATCH_KEYS)
    added: list[str] = []
    if name in DISPATCHABLE_SKILLS:
        newline = _newline_of(kept or opening)
        added.append(f"subagent: true{newline}")
        if agent is not None:
            added.append(f"agent: {agent}{newline}")
    if kept == front and not added:
        return text
    return "".join(opening + kept + added + rest)


# ---------------------------------------------------------------------------
# Codex — perfil como ``~/.codex/agents/<nome>.toml``
# ---------------------------------------------------------------------------

# O escape do JSON é subconjunto do de string básica TOML, então
# ``json.dumps`` serve sem depender de biblioteca de TOML. O DEL (U+007F)
# o JSON deixa cru e o TOML proíbe — sai como ``\uXXXX``.
_CONTROLE_TOML = re.compile("[\x7f]")


def _toml_string(valor: str) -> str:
    return _CONTROLE_TOML.sub(
        lambda m: f"\\u{ord(m.group()):04X}",
        json.dumps(valor, ensure_ascii=False),
    )


def _codex_toml(text: str) -> str:
    """O perfil no formato de ``~/.codex/agents/<nome>.toml``.

    Chaves de topo ``name``, ``description`` e ``developer_instructions``
    (o corpo depois do frontmatter, com LF). Perfil sem ``name`` ou sem
    ``description`` levanta: o Codex exige os dois, e inventar a
    descrição publicaria um papel que ninguém escreveu.
    """
    parsed = split_frontmatter(text)
    if parsed is None:
        raise ValueError("perfil sem frontmatter não vira agent do Codex")
    _, front, rest = parsed
    name = frontmatter_scalar(front, "name")
    description = frontmatter_scalar(front, "description")
    if not name or not description:
        raise ValueError(
            "perfil sem `name` ou sem `description` não vira agent do "
            f"Codex: {name!r}"
        )
    corpo = "".join(rest[1:]).replace("\r\n", "\n").lstrip("\n")
    return (
        f"name = {_toml_string(name)}\n"
        f"description = {_toml_string(description)}\n"
        f"developer_instructions = {_toml_string(corpo)}\n"
    )


# ---------------------------------------------------------------------------
# O render por host
# ---------------------------------------------------------------------------


def layout_for(host: str, scope: str) -> HostLayout | None:
    """O layout de ``host`` em ``scope``, ou ``None`` se não homologado."""
    layouts = USER_LAYOUTS if scope == "user" else PROJECT_LAYOUTS
    return layouts.get(host)


def render_hosts(
    catalog: AssetCatalog, *, hosts: Sequence[str], scope: str
) -> dict[str, bytes]:
    """``{caminho relativo à raiz: bytes}`` para cada host homologado.

    Host sem layout (``cursor`` e desconhecidos) não rende nada — a
    seleção em si é validada antes, em ``service._hosts``. Colisões de
    superfície compartilhada (``.agents/``) resolvem pela mesma
    renderização: devin, codex e copilot escrevem o mesmo conteúdo lá.
    """
    declarants = _declarants(catalog.agents)
    out: dict[str, bytes] = {}
    for host in sorted(set(hosts)):
        layout = layout_for(host, scope)
        if layout is None:
            continue
        for name, files in sorted(catalog.skills.items()):
            for skill_dir in layout.skill_dirs:
                for inner, data in sorted(files.items()):
                    if inner == "SKILL.md":
                        data = render_skill(
                            data.decode("utf-8"),
                            layout.skill_platform,
                            name=name,
                            agent=_agent_for_skill(name, declarants),
                        ).encode("utf-8")
                    out[f"{skill_dir}/{name}/{inner}"] = data
        for stem, data in sorted(catalog.agents.items()):
            if stem in DEVIN_BUILTIN_PROFILE_NAMES:
                raise ValueError(
                    f"perfil colide com built-in do Devin: {stem!r}"
                )
            for agent_dir in layout.agent_dirs:
                rel = layout.agent_pattern.format(stem=stem)
                out[f"{agent_dir}/{rel}"] = render_agent(
                    data.decode("utf-8"), layout.agent_platform
                ).encode("utf-8")
        for rel, data in sorted(catalog.overlays.get(host, {}).items()):
            out[rel] = data
    return dict(sorted(out.items()))


__all__ = [
    "AGENT_PLATFORMS",
    "DEVIN_BUILTIN_PROFILE_NAMES",
    "DEVIN_DROPPED_AGENT_KEYS",
    "DEVIN_SKILL_DISPATCH_KEYS",
    "DISPATCHABLE_SKILLS",
    "NON_DISPATCHABLE_SKILLS",
    "ORCHESTRATOR_PROFILES",
    "PROJECT_LAYOUTS",
    "SKILL_DISPATCH_REASON",
    "UNSUPPORTED_HOSTS",
    "USER_LAYOUTS",
    "AssetCatalog",
    "HostLayout",
    "frontmatter_scalar",
    "layout_for",
    "render_agent",
    "render_hosts",
    "render_skill",
    "split_frontmatter",
]
