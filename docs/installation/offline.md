# Instalação offline

O core não faz network I/O. Para ambientes air-gapped:

1. Baixe a wheel numa máquina com rede (ou use o checkout).
2. `pip install data_sentinel-0.1.0-py3-none-any.whl --no-index`
3. `data-sentinel install` — zero downloads; assets estão na wheel.

Doctor/MCP-verify funcionam offline. Conectores AWS são opt-in via
extra `aws` + credenciais — sem elas, nada é tentado.
