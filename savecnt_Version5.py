import vobject
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
import re
import pickle
import os
import logging
import json
from datetime import datetime
import sys
import time
from multiprocessing import Process

# Configurar logging apenas para arquivo, sem output no console
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot_contatos.log"),
    ]
)
logger = logging.getLogger(__name__)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

def carregar_contatos():
    try:
        if os.path.exists('contatos_salvos.pkl'):
            with open('contatos_salvos.pkl', 'rb') as f:
                return pickle.load(f)
    except Exception as e:
        logger.error(f"Erro ao carregar contatos: {e}")
        if os.path.exists('contatos_salvos.pkl'):
            os.remove('contatos_salvos.pkl')
    return {}

def salvar_contatos():
    try:
        with open('contatos_salvos.pkl', 'wb') as f:
            pickle.dump(contatos_por_usuario, f)
    except Exception as e:
        logger.error(f"Erro ao salvar contatos: {e}")

def carregar_token():
    try:
        if os.path.exists('token_salvo.txt'):
            with open('token_salvo.txt', 'r') as f:
                return f.read().strip()
    except Exception as e:
        logger.error(f"Erro ao carregar token: {e}")
    return None

def salvar_token(token):
    try:
        with open('token_salvo.txt', 'w') as f:
            f.write(token)
    except Exception as e:
        logger.error(f"Erro ao salvar token: {e}")

def remover_token():
    try:
        if os.path.exists('token_salvo.txt'):
            os.remove('token_salvo.txt')
        return True
    except Exception as e:
        logger.error(f"Erro ao remover token: {e}")
        return False

contatos_por_usuario = carregar_contatos()

def limpar_numero(numero):
    numero_limpo = re.sub(r'[^\d]', '', numero)
    if numero_limpo.startswith('55'):
        numero_limpo = numero_limpo[2:]
    return numero_limpo

def validar_numero_brasileiro(numero):
    numero_limpo = limpar_numero(numero)
    if len(numero_limpo) not in [10, 11]:
        return False
    return True

def contato_existe(user_id, nome, numero):
    return any((c[0].lower() == nome.lower() and c[1] == numero) for c in contatos_por_usuario.get(user_id, {}).get("contatos", []))

def salvar_vcf(contatos):
    vcf_texto = ""
    for c in contatos:
        nome_linha = c[0]
        numero = c[1]
        if ' - ' in nome_linha:
            nome, categoria = nome_linha.split(' - ', 1)
        else:
            nome = nome_linha
            categoria = "Sem categoria"
        contato_completo = f"{nome} - {categoria}"
        numero_formatado = "+55" + numero

        card = vobject.vCard()
        card.add('fn').value = contato_completo

        nome_split = nome.split(' ', 1)
        sobrenome = nome_split[1] if len(nome_split) > 1 else ''
        name_obj = vobject.vcard.Name(family=sobrenome, given=nome_split[0])
        card.add('n').value = name_obj

        tel = card.add('tel')
        tel.type_param = ['CELL']
        tel.value = numero_formatado
        card.add('note').value = f"Categoria: {categoria}"
        vcf_texto += card.serialize()

    with open("contatos.vcf", "w", encoding="utf-8") as f:
        f.write(vcf_texto)
    return "contatos.vcf"

def salvar_csv(contatos):
    csv_texto = "Nome,Número,Categoria\n"
    for c in contatos:
        nome_linha = c[0]
        numero = c[1]
        if ' - ' in nome_linha:
            nome, categoria = nome_linha.split(' - ', 1)
        else:
            nome = nome_linha
            categoria = "Sem categoria"
        csv_texto += f'"{nome}","+55{numero}","{categoria}"\n'

    with open("contatos.csv", "w", encoding="utf-8") as f:
        f.write(csv_texto)
    return "contatos.csv"

def salvar_json(contatos):
    contatos_lista = []
    for c in contatos:
        nome_linha = c[0]
        numero = c[1]
        if ' - ' in nome_linha:
            nome, categoria = nome_linha.split(' - ', 1)
        else:
            nome = nome_linha
            categoria = "Sem categoria"
        contatos_lista.append({
            "nome": nome,
            "numero": f"+55{numero}",
            "categoria": categoria
        })

    with open("contatos.json", "w", encoding="utf-8") as f:
        json.dump(contatos_lista, f, ensure_ascii=False, indent=2)
    return "contatos.json"

# ------------------- HANDLERS DO BOT -------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    num_contatos = len(contatos_por_usuario.get(user_id, {}).get("contatos", []))
    await update.message.reply_text(
        f"👋 Olá! Envie os contatos no formato:\n\n"
        "Nome 1\nNúmero 1\nNome 2\nNúmero 2\n...\n\n"
        f"Contatos na lista: {num_contatos} números\n\n"
        "Para ver todos os comandos e dicas, use /ajuda"
    )

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE, pagina=0):
    paginas_ajuda = [
        "📋 *COMANDOS DISPONÍVEIS*\n\n"
        "• /start - Mensagem de boas-vindas\n"
        "• /ajuda - Mostra esta ajuda\n"
        "• /arquivo - Exportar contatos em vários formatos\n"
        "• /listar - Ver contatos adicionados\n"
        "• /remover - Remover contatos\n"
        "• /editar - Editar um contato\n"
        "• /apagar - Limpar todos os contatos\n\n"
        "Use os botões abaixo para navegar ➡️",
        "💡 *DICAS DE FORMATAÇÃO*\n\n"
        "• Use o formato: Nome - Categoria\n  Ex: João Silva - Trabalho\n\n"
        "• Categorias ajudam a organizar seus contatos\n\n"
        "• Números aceitos:\n  - +55 82 9961-0303\n  - 82 9961-0303\n  - 8299610303\n\n"
        "➡️ Próxima página",
        "📤 *DICAS DE EXPORTAÇÃO*\n\n"
        "• .VCF - Padrão universal para contatos\n"
        "• .CSV - Planilhas Excel/Google Sheets\n"
        "• .JSON - Para desenvolvedores\n\n"
        "• Use /arquivo para escolher o formato\n\n"
        "• Faça backup regular dos seus contatos\n\n"
        "⬅️ Voltar para comandos"
    ]
    keyboard = []
    if pagina > 0:
        keyboard.append([InlineKeyboardButton("⬅️ Anterior", callback_data=f"ajuda_pagina:{pagina-1}")])
    if pagina < len(paginas_ajuda) - 1:
        if keyboard:
            keyboard[0].append(InlineKeyboardButton("Próxima ➡️", callback_data=f"ajuda_pagina:{pagina+1}"))
        else:
            keyboard.append([InlineKeyboardButton("Próxima ➡️", callback_data=f"ajuda_pagina:{pagina+1}")])
    markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    if update.callback_query:
        await update.callback_query.edit_message_text(
            paginas_ajuda[pagina],
            parse_mode='Markdown',
            reply_markup=markup
        )
        await update.callback_query.answer()
    else:
        msg = await update.message.reply_text(
            paginas_ajuda[pagina],
            parse_mode='Markdown',
            reply_markup=markup
        )
        user_id = update.effective_user.id
        if user_id not in contatos_por_usuario:
            contatos_por_usuario[user_id] = {"contatos": []}
        contatos_por_usuario[user_id]["msg_ajuda_id"] = msg.message_id

async def arquivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in contatos_por_usuario or not contatos_por_usuario[user_id]["contatos"]:
        await update.message.reply_text("❌ Nenhum contato adicionado ainda.")
        return
    keyboard = [
        [InlineKeyboardButton(".VCF - Para contatos", callback_data="exportar_vcf")],
        [InlineKeyboardButton(".CSV - Para planilhas", callback_data="exportar_csv")],
        [InlineKeyboardButton(".JSON - Para desenvolvedores", callback_data="exportar_json")],
        [InlineKeyboardButton("TODOS os formatos", callback_data="exportar_todos")]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "📤 Escolha o formato em que deseja salvar:",
        reply_markup=markup
    )

async def listar(update: Update, context: ContextTypes.DEFAULT_TYPE, pagina=0):
    user_id = update.effective_user.id
    if user_id not in contatos_por_usuario or not contatos_por_usuario[user_id]["contatos"]:
        await update.message.reply_text("❌ Nenhum contato adicionado ainda.")
        return
    if "ordenacao" not in contatos_por_usuario[user_id]:
        contatos_por_usuario[user_id]["ordenacao"] = "padrao"
    ordenacao = contatos_por_usuario[user_id].get("ordenacao", "padrao")
    if ordenacao == "alfabetica":
        contatos_ordenados = sorted(contatos_por_usuario[user_id]["contatos"], key=lambda x: x[0].lower())
        texto_botao = "Padrão"
        nova_ordenacao = "padrao"
    else:
        contatos_ordenados = contatos_por_usuario[user_id]["contatos"]
        texto_botao = "Ordem ABCD"
        nova_ordenacao = "alfabetica"
    contatos_por_pagina = 25
    total_paginas = (len(contatos_ordenados) + contatos_por_pagina - 1) // contatos_por_pagina
    inicio = pagina * contatos_por_pagina
    fim = min((pagina + 1) * contatos_por_pagina, len(contatos_ordenados))
    contatos_pagina = contatos_ordenados[inicio:fim]
    total_contatos = len(contatos_ordenados)
    categorias = {}
    for nome, numero in contatos_ordenados:
        if ' - ' in nome:
            _, categoria = nome.split(' - ', 1)
        else:
            categoria = "Sem categoria"
        categorias[categoria] = categorias.get(categoria, 0) + 1
    stats_texto = f"📊 Estatísticas:\nTotal: {total_contatos} contatos\n"
    for categoria, quantidade in categorias.items():
        stats_texto += f"- {categoria}: {quantidade}\n"
    contatos_texto = "\n".join([f"- {c[0]} (+55 {c[1]})" for c in contatos_pagina])
    keyboard = [[InlineKeyboardButton(texto_botao, callback_data=f"alterar_ordenacao:{nova_ordenacao}:{pagina}")]]
    if total_paginas > 1:
        nav_buttons = []
        if pagina > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"pagina:{pagina-1}"))
        if pagina < total_paginas - 1:
            nav_buttons.append(InlineKeyboardButton("Próxima ➡️", callback_data=f"pagina:{pagina+1}"))
        keyboard.append(nav_buttons)
    markup = InlineKeyboardMarkup(keyboard)
    msg = await update.message.reply_text(
        f"{stats_texto}\n📒 Seus contatos (página {pagina+1}/{total_paginas}):\n{contatos_texto}", 
        reply_markup=markup
    )
    contatos_por_usuario[user_id]["msg_listar_id"] = msg.message_id
    salvar_contatos()

async def apagar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    contatos_por_usuario[user_id] = {"contatos": []}
    salvar_contatos()
    await update.message.reply_text("✅ Todos os contatos foram removidos!")

def procurar_contatos_por_nome(contatos, nome_busca):
    nome_busca = nome_busca.strip().lower()
    encontrados = [(i, c) for i, c in enumerate(contatos) if nome_busca in c[0].lower()]
    return encontrados

async def remover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in contatos_por_usuario or not contatos_por_usuario[user_id]["contatos"]:
        await update.message.reply_text("❌ Nenhum contato adicionado ainda.")
        return

    keyboard = [
        [InlineKeyboardButton("Apagar 1 contato", callback_data="remover_um")],
        [InlineKeyboardButton("Apagar contatos em lote", callback_data="remover_lote")]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Remover contatos! Escolha qual você quer ↓",
        reply_markup=markup
    )

async def editar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in contatos_por_usuario or not contatos_por_usuario[user_id]["contatos"]:
        await update.message.reply_text("❌ Nenhum contato adicionado ainda.")
        return

    contatos_por_usuario[user_id]["modo_edicao"] = "selecionar"
    await update.message.reply_text("❓ Qual contato você quer editar? Digite o nome exato ou parte dele.")

async def processar_editar_nome(update, context, nome_para_editar):
    user_id = update.effective_user.id
    contatos_atuais = contatos_por_usuario[user_id]["contatos"]
    encontrados = procurar_contatos_por_nome(contatos_atuais, nome_para_editar)

    if not encontrados:
        keyboard = [
            [InlineKeyboardButton("Tentar outro", callback_data="editar_outro")],
            [InlineKeyboardButton("Cancelar", callback_data="cancelar_edicao")]
        ]
        markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "⚠️ Nenhum contato encontrado com esse nome.",
            reply_markup=markup
        )
        return

    if len(encontrados) == 1:
        idx, contato = encontrados[0]
        contatos_por_usuario[user_id]["contato_editando"] = idx
        contatos_por_usuario[user_id]["modo_edicao"] = "dados"
        await update.message.reply_text(
            f"📝 Editando: {contato[0]} (+55 {contato[1]})\n\n"
            "Envie os novos dados no formato:\n"
            "Nome - Categoria\nNúmero\n\n"
            "Exemplo:\n"
            "João Silva - Trabalho\n8299610303"
        )
    else:
        contatos_por_usuario[user_id]["edicao_indices"] = [idx for idx, _ in encontrados]
        keyboard = [
            [InlineKeyboardButton(f"{c[0]} (+55 {c[1]})", callback_data=f"selecionar_editar:{idx}")]
            for idx, c in encontrados
        ]
        keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_edicao")])
        markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🔎 Foram encontrados vários contatos com esse nome — clique em um para editar:",
            reply_markup=markup
        )

async def processar_remover_nome(update, context, nome_para_remover):
    user_id = update.effective_user.id
    contatos_atuais = contatos_por_usuario[user_id]["contatos"]
    encontrados = procurar_contatos_por_nome(contatos_atuais, nome_para_remover)

    if not encontrados:
        keyboard = [
            [InlineKeyboardButton("Remover outro", callback_data="remover_outra")],
            [InlineKeyboardButton("Adicionar contatos", callback_data="adicionar_contatos")]
        ]
        markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "⚠️ Nenhum contato encontrado com esse nome.",
            reply_markup=markup
        )
        return

    if len(encontrados) == 1:
        idx, contato = encontrados[0]
        contatos_por_usuario[user_id]["confirm_remover"] = idx
        keyboard = [
            [InlineKeyboardButton("Sim", callback_data="confirmar_remover")],
            [InlineKeyboardButton("Não", callback_data="cancelar_remover")]
        ]
        markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"Quer mesmo excluir {contato[0]} (+55 {contato[1]})?",
            reply_markup=markup
        )
    else:
        contatos_por_usuario[user_id]["remocao_indices"] = [idx for idx, _ in encontrados]
        keyboard = [
            [InlineKeyboardButton(f"{c[0]} (+55 {c[1]})", callback_data=f"selecionar_remover:{idx}")]
            for idx, c in encontrados
        ]
        keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_remocao")])
        markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🔎 Foram encontrados vários contatos com esse nome — clique em um para apagar:",
            reply_markup=markup
        )

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.startswith("ajuda_pagina:"):
        pagina = int(data.split(":")[1])
        await ajuda(update, context, pagina)
        return

    elif data.startswith("pagina:"):
        pagina = int(data.split(":")[1])
        await listar(update, context, pagina)
        return

    elif data.startswith("alterar_ordenacao:"):
        partes = data.split(":")
        nova_ordenacao = partes[1]
        pagina = int(partes[2])
        contatos_por_usuario[user_id]["ordenacao"] = nova_ordenacao
        await listar(update, context, pagina)
        return

    elif data == "exportar_vcf":
        contatos = contatos_por_usuario[user_id]["contatos"]
        arquivo = salvar_vcf(contatos)
        await query.message.reply_document(
            document=InputFile(arquivo, filename="contatos.vcf", mime_type="text/x-vcard"),
            caption="📇 Aqui estão seus contatos no formato VCF!"
        )
        os.remove(arquivo)
        await query.message.delete()
        contatos_por_usuario[user_id]["aguardando_confirmacao_apagar"] = True
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Deseja apagar a lista atual e criar uma nova? (Sim ou Não)"
        )
        return

    elif data == "exportar_csv":
        contatos = contatos_por_usuario[user_id]["contatos"]
        arquivo = salvar_csv(contatos)
        await query.message.reply_document(
            document=InputFile(arquivo, filename="contatos.csv", mime_type="text/csv"),
            caption="📊 Aqui estão seus contatos no formato CSV!"
        )
        os.remove(arquivo)
        await query.message.delete()
        contatos_por_usuario[user_id]["aguardando_confirmacao_apagar"] = True
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Deseja apagar a lista atual e criar uma nova? (Sim ou Não)"
        )
        return

    elif data == "exportar_json":
        contatos = contatos_por_usuario[user_id]["contatos"]
        arquivo = salvar_json(contatos)
        await query.message.reply_document(
            document=InputFile(arquivo, filename="contatos.json", mime_type="application/json"),
            caption="📝 Aqui estão seus contatos no formato JSON!"
        )
        os.remove(arquivo)
        await query.message.delete()
        contatos_por_usuario[user_id]["aguardando_confirmacao_apagar"] = True
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Deseja apagar a lista atual e criar uma nova? (Sim ou Não)"
        )
        return

    elif data == "exportar_todos":
        contatos = contatos_por_usuario[user_id]["contatos"]
        arquivos = []
        try:
            arquivos.append(salvar_vcf(contatos))
            arquivos.append(salvar_csv(contatos))
            arquivos.append(salvar_json(contatos))
            media = [
                InputFile(arquivos[0], filename="contatos.vcf", mime_type="text/x-vcard"),
                InputFile(arquivos[1], filename="contatos.csv", mime_type="text/csv"),
                InputFile(arquivos[2], filename="contatos.json", mime_type="application/json"),
            ]
            await query.message.reply_media_group(media=media)
            await query.message.reply_text("📦 Todos os formatos exportados!")
        finally:
            for arquivo in arquivos:
                if os.path.exists(arquivo):
                    os.remove(arquivo)
        await query.message.delete()
        contatos_por_usuario[user_id]["aguardando_confirmacao_apagar"] = True
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Deseja apagar a lista atual e criar uma nova? (Sim ou Não)"
        )
        return

    # ... demais callbacks de remover, editar etc. permanecem iguais ...

    logger.warning(f"Callback não tratado: {data}")
    await query.edit_message_text("❌ Ação não reconhecida.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id not in contatos_por_usuario:
        contatos_por_usuario[user_id] = {"contatos": []}
    
    # FLUXO DE CONFIRMAÇÃO DE APAGAR LISTA APÓS EXPORTAÇÃO
    if contatos_por_usuario.get(user_id, {}).get("aguardando_confirmacao_apagar", False):
        resposta = text.lower()
        if resposta in ["sim", "s"]:
            contatos_por_usuario[user_id]["contatos"] = []
            contatos_por_usuario[user_id]["aguardando_confirmacao_apagar"] = False
            await update.message.reply_text("✅ Lista apagada! Envie os novos contatos.")
            salvar_contatos()
            return
        elif resposta in ["não", "nao", "n"]:
            contatos_por_usuario[user_id]["aguardando_confirmacao_apagar"] = False
            await update.message.reply_text("👍 Lista mantida! Envie os contatos para adicionar.")
            return
        else:
            # Pergunta novamente, de forma clara e explicativa
            await update.message.reply_text(
                "Olá! Você quer apagar a lista atual para criar uma nova? (Sim ou Não)\n\n"
                "Se você responder 'Sim', a lista atual será excluída e você pode começar uma nova.\n"
                "Se responder 'Não', os novos contatos serão adicionados à lista existente."
            )
            return

    modo_remocao = contatos_por_usuario[user_id].get("modo_remocao")
    modo_edicao = contatos_por_usuario[user_id].get("modo_edicao")
    awaiting_remover_name = contatos_por_usuario[user_id].get("awaiting_remover_name", False)

    if modo_edicao == "selecionar":
        await processar_editar_nome(update, context, text)
        return

    elif modo_edicao == "dados":
        idx = contatos_por_usuario[user_id].get("contato_editando")
        if idx is not None and 0 <= idx < len(contatos_por_usuario[user_id]["contatos"]):
            linhas = text.splitlines()
            if len(linhas) < 2:
                await update.message.reply_text("⚠️ Formato inválido. Envie no formato:\nNome - Categoria\nNúmero")
                return
            novo_nome = linhas[0].strip()
            novo_numero = linhas[1].strip()
            numero_limpo = limpar_numero(novo_numero)
            if not validar_numero_brasileiro(numero_limpo):
                await update.message.reply_text("❌ Número inválido. Deve ter 10 ou 11 dígitos (DDD + número).")
                return
            contato_antigo = contatos_por_usuario[user_id]["contatos"][idx]
            contatos_por_usuario[user_id]["contatos"][idx] = (novo_nome, numero_limpo)
            keyboard = [
                [InlineKeyboardButton("Editar outro", callback_data="editar_outro")],
                [InlineKeyboardButton("Voltar ao menu", callback_data="adicionar_contatos")]
            ]
            markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"✅ Contato editado com sucesso!\n\n"
                f"Antes: {contato_antigo[0]} (+55 {contato_antigo[1]})\n"
                f"Depois: {novo_nome} (+55 {numero_limpo})",
                reply_markup=markup
            )
            contatos_por_usuario[user_id].pop("modo_edicao", None)
            contatos_por_usuario[user_id].pop("contato_editando", None)
            salvar_contatos()
        return

    elif awaiting_remover_name and modo_remocao == "individual":
        contatos_por_usuario[user_id].pop("awaiting_remover_name", None)
        await processar_remover_nome(update, context, text)
        return

    elif modo_remocao == "lote":
        linhas = text.splitlines()
        if len(linhas) % 2 != 0:
            await update.message.reply_text("⚠️ Formato inválido. Cada nome deve ser seguido de um número.")
            return
        contatos_para_remover = []
        for i in range(0, len(linhas), 2):
            nome = linhas[i].strip()
            numero = linhas[i+1].strip()
            numero_limpo = limpar_numero(numero)
            if nome and numero_limpo:
                contatos_para_remover.append((nome, numero_limpo))
        if "contatos_lote" not in contatos_por_usuario[user_id]:
            contatos_por_usuario[user_id]["contatos_lote"] = []
        contatos_por_usuario[user_id]["contatos_lote"].extend(contatos_para_remover)
        contatos_texto = "\n".join([f"❌ {c[0]} - {c[1]}" for c in contatos_por_usuario[user_id]["contatos_lote"]])
        keyboard = [
            [InlineKeyboardButton("✅ Confirmar exclusão", callback_data="confirmar_lote")],
            [InlineKeyboardButton("➕ Adicionar mais", callback_data="continuar_lote")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_lote")]
        ]
        markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"📋 Contatos selecionados para remoção:\n\n{contatos_texto}\n\n"
            "Deseja confirmar a exclusão ou adicionar mais contatos?",
            reply_markup=markup
        )
        return

    if text.lower() == "/apagar":
        await apagar(update, context)
        return

    linhas = text.splitlines()
    if len(linhas) % 2 != 0:
        await update.message.reply_text("⚠️ Formato inválido. Cada nome deve ser seguido de um número.")
        return

    novos_contatos = []
    contatos_duplicados = []
    for i in range(0, len(linhas), 2):
        nome = linhas[i].strip()
        numero = linhas[i + 1].strip()
        numero_limpo = limpar_numero(numero)
        if not validar_numero_brasileiro(numero_limpo):
            await update.message.reply_text(f"❌ Número inválido: {numero}. Deve ter 10 ou 11 dígitos (DDD + número).")
            continue
        if nome and numero_limpo:
            if contato_existe(user_id, nome, numero_limpo):
                contatos_duplicados.append((nome, numero_limpo))
            else:
                novos_contatos.append((nome, numero_limpo))

    if novos_contatos:
        contatos_por_usuario[user_id]["contatos"].extend(novos_contatos)
        salvar_contatos()
        msg = f"✅ {len(novos_contatos)} contato(s) adicionados."
        if contatos_duplicados:
            msg += f"\n⚠️ {len(contatos_duplicados)} contato(s) já existiam e não foram adicionados."
        msg += "\nUse /arquivo para gerar o .vcf."
        await update.message.reply_text(msg)
    else:
        msg = "❌ Nenhum contato válido foi adicionado."
        if contatos_duplicados:
            msg += f"\n⚠️ {len(contatos_duplicados)} contato(s) já existiam e não foram adicionados."
        await update.message.reply_text(msg)

# ---------------- FIM DOS HANDLERS ---------------------

def mostrar_banner():
    os.system('clear' if os.name != 'nt' else 'cls')
    print("=" * 50)
    print("            BEM-VINDO AO SAVECNT")
    print("=" * 50)
    print()

def mostrar_menu_principal():
    os.system('clear' if os.name != 'nt' else 'cls')
    print("=" * 50)
    print("                  SAVECNT")
    print("=" * 50)
    print()
    print("1. Logout")
    print("2. Encerrar programa")
    print()
    print("Digite o número da opção desejada:")

def menu_principal_loop(bot_process):
    while True:
        mostrar_menu_principal()
        opcao = input().strip()
        if opcao == "1":
            if remover_token():
                print("Token removido com sucesso! Reiniciando...")
                time.sleep(2)
                bot_process.terminate()
                bot_process.join()
                python = sys.executable
                os.execl(python, python, *sys.argv)
            else:
                print("Erro ao remover token. Tente novamente.")
                time.sleep(2)
        elif opcao == "2":
            print("Bot encerrado com sucesso, te espero em breve <3")
            time.sleep(2)
            bot_process.terminate()
            bot_process.join()
            sys.exit(0)
        else:
            print("Opção inválida. Tente novamente.")
            time.sleep(2)

def iniciar_bot(token):
    global contatos_por_usuario
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ajuda", ajuda))
    app.add_handler(CommandHandler("arquivo", arquivo))
    app.add_handler(CommandHandler("listar", listar))
    app.add_handler(CommandHandler("remover", remover))
    app.add_handler(CommandHandler("editar", editar))
    app.add_handler(CommandHandler("apagar", apagar))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    logger.info("Bot iniciado com sucesso!")
    print("🤖 Bot rodando...")
    try:
        app.run_polling()
    except KeyboardInterrupt:
        logger.info("Bot interrompido pelo usuário")
        print("👋 Bot encerrado <3.")
    except Exception as e:
        logger.error(f"Erro ao executar o bot: {e}")
        print(f"❌ Erro: {e}")
    finally:
        salvar_contatos()

def main():
    token_salvo = carregar_token()
    if token_salvo:
        bot_process = Process(target=iniciar_bot, args=(token_salvo,), daemon=True)
        bot_process.start()
        menu_principal_loop(bot_process)
    else:
        mostrar_banner()
        print("Adicione o token do seu bot do Telegram:")
        while True:
            token = input().strip()
            if not token:
                print("Token não pode estar vazio. Tente novamente:")
                continue
            if not token.count(":") > 0:
                print("Token inválido. Formato esperado: 123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ")
                print("Digite novamente:")
                continue
            salvar_token(token)
            print("✅ Token salvo com sucesso! :D")
            time.sleep(2)
            break
        python = sys.executable
        os.execl(python, python, *sys.argv)

if __name__ == "__main__":
    main()