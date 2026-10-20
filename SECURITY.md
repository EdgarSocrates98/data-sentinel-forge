# Política de Segurança

## Reportar vulnerabilidades

Não abra issues públicas para vulnerabilidades. Use o GitHub Security Advisories do repositório (`Security → Report a vulnerability`) ou contate o mantenedor pelo perfil `@EdgarSocrates98`.

## Postura de segurança do produto

- Operação **read-only** por padrão: análise local de artefatos, sem chamadas de escrita a serviços externos.
- Análise local funciona **sem credenciais AWS**.
- Guardas de caminho contra path traversal; limites de tamanho e processamento de arquivos.
- Redação automática de segredos (tokens, chaves AWS, senhas) antes de persistir ou exibir evidências.
- Nenhum comando encontrado em logs/arquivos analisados é executado.

## Cycle 03 — garantias adicionais

- Nenhum SQL/DML recebido é executado — somente parsing estático.
- Metadata URLs nunca são seguidas; locations são texto.
- Decrypt KMS nunca é executado como teste.
- Ausência de visibilidade de permissões é reportada como UNKNOWN,
  nunca como negação.
