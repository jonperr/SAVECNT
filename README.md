# SaveCNT – Bot de Contatos para Telegram

Um bot para gerenciar contatos diretamente pelo Telegram, com suporte para exportação em VCF, CSV e JSON, interface interativa e persistência local dos dados.

## Recursos principais

Adicione contatos enviando mensagens no formato:

- Nome - Categoria
- Número

Exportação em múltiplos formatos:

.vcf (importação direta em celulares)

.csv (planilhas Excel/Google Sheets)

.json (para desenvolvedores)


Organização por categorias (ex.: "Trabalho", "Família", etc.).

Edição e remoção de contatos individuais ou em lote.

Listagem com estatísticas de categorias e ordenação alfabética.

Persistência automática (salvamento em arquivo .pkl).

Menu CLI para encerrar ou reiniciar o bot sem perder os contatos.

Integração com Python Telegram Bot v20+ usando ApplicationBuilder.



---

# Instalação

1. Instale as dependências:

```
pip install -r requirements.txt
```


2. Clone o repositório:

```
git clone https://github.com/jonperr/SaveCnt.git
cd SaveCnt
```


3. dê o comando para iniciar:

```
python savecnt.py
```


---

# Uso

## 1. Obtenha um token para o seu bot com o BotFather.

Na primeira execução, insira o token do bot quando solicitado.

O token será salvo em token_salvo.txt para as próximas execuções.



## 2. Use o menu no terminal para:

Logout (remover token)

Encerrar o bot



## 3. Comandos disponíveis no bot (Telegram):

/start – Mensagem inicial

/ajuda – Guia de comandos e dicas

/arquivo – Exportar contatos

/listar – Ver contatos e estatísticas

/remover – Excluir contatos

/editar – Alterar contatos existentes

/apagar – Limpar toda a lista





---

# Exportação

VCF → Importação direta em celulares.

CSV → Abrir em Excel ou Google Sheets.

JSON → Integrar com sistemas externos.


Os arquivos são salvos na pasta local do projeto após cada exportação.


– IA