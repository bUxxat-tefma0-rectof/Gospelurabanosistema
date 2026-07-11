import mercadopago
import base64
from io import BytesIO
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode
import os
import asyncio

# ============ CONFIGURAÇÕES DIRETAS ============
BOT_TOKEN = "8603436205:AAGxsylTMG_4vd3madNaEaCh7sHu0-uKxio"
MERCADO_PAGO_TOKEN = "APP_USR-2096088157710260-021219-167b045d03f4904a28401b79190d54eb-2069324095"

# Inicializar Mercado Pago
sdk = mercadopago.SDK(MERCADO_PAGO_TOKEN)

# Armazenamento em memória
pagamentos = {}

# ============ FUNÇÕES DO BOT ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start - Menu principal"""
    keyboard = [
        [InlineKeyboardButton("💵 R$ 10", callback_data="pix_10")],
        [InlineKeyboardButton("💵 R$ 50", callback_data="pix_50")],
        [InlineKeyboardButton("💵 R$ 100", callback_data="pix_100")],
        [InlineKeyboardButton("💵 R$ 200", callback_data="pix_200")],
    ]
    
    await update.message.reply_text(
        "💳 *Recarga PIX*\n\nEscolha o valor:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def gerar_pix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gera QR Code PIX"""
    query = update.callback_query
    await query.answer()
    
    valor = float(query.data.replace("pix_", ""))
    user = query.from_user
    
    try:
        # Criar pagamento no Mercado Pago
        resultado = sdk.payment().create({
            "transaction_amount": valor,
            "description": f"Recarga R$ {valor:.2f}",
            "payment_method_id": "pix",
            "payer": {
                "email": f"user{user.id}@telegram.com",
                "first_name": user.first_name
            },
            "date_of_expiration": (datetime.utcnow() + timedelta(minutes=30)).strftime(
                "%Y-%m-%dT%H:%M:%S.000-03:00"
            )
        })
        
        pagamento = resultado["response"]
        mp_id = pagamento["id"]
        qr_base64 = pagamento["point_of_interaction"]["transaction_data"]["qr_code_base64"]
        copia_cola = pagamento["point_of_interaction"]["transaction_data"]["qr_code"]
        
        # Salvar na memória
        pagamentos[mp_id] = {
            "user_id": user.id,
            "username": user.first_name,
            "valor": valor,
            "status": "pending"
        }
        
        # Converter QR Code
        qr_image = base64.b64decode(qr_base64)
        
        # Botão de verificar
        keyboard = [
            [InlineKeyboardButton("🔄 Verificar Pagamento", callback_data=f"ver_{mp_id}")]
        ]
        
        # Enviar QR Code
        await query.message.reply_photo(
            BytesIO(qr_image),
            caption=(
                f"📱 *PAGAMENTO PIX*\n\n"
                f"💰 Valor: R$ {valor:.2f}\n"
                f"🆔 ID: `{mp_id}`\n\n"
                f"📋 *PIX Copia e Cola:*\n"
                f"`{copia_cola}`\n\n"
                f"⏰ Expira em 30 minutos\n\n"
                f"⚠️ Após pagar, clique em *Verificar Pagamento*"
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Apagar mensagem antiga
        await query.message.delete()
        
        print(f"✅ PIX gerado: {mp_id} | R$ {valor:.2f} | {user.first_name}")
        
    except Exception as e:
        erro = str(e)
        print(f"❌ Erro PIX: {erro}")
        await query.edit_message_text(
            f"❌ Erro ao gerar PIX\n\n`{erro[:200]}`",
            parse_mode=ParseMode.MARKDOWN
        )

async def verificar_pagamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verifica status do pagamento"""
    query = update.callback_query
    await query.answer()
    
    mp_id = query.data.replace("ver_", "")
    
    try:
        resultado = sdk.payment().get(mp_id)
        status = resultado["response"]["status"]
        
        # Atualizar memória
        if mp_id in pagamentos:
            pagamentos[mp_id]["status"] = status
        
        # Mensagem por status
        if status == "approved":
            mensagem = (
                f"✅ *PAGAMENTO APROVADO!*\n\n"
                f"💰 Valor: R$ {pagamentos.get(mp_id, {}).get('valor', 0):.2f}\n"
                f"🎉 Recarga realizada com sucesso!\n\n"
                f"Obrigado pela preferência!"
            )
            keyboard = [[InlineKeyboardButton("💳 Nova Recarga", callback_data="nova_recarga")]]
            
        elif status == "pending":
            mensagem = (
                f"⏳ *PAGAMENTO PENDENTE*\n\n"
                f"Aguardando confirmação...\n"
                f"Clique novamente para verificar."
            )
            keyboard = [[InlineKeyboardButton("🔄 Verificar Novamente", callback_data=f"ver_{mp_id}")]]
            
        elif status == "rejected":
            mensagem = "❌ Pagamento rejeitado. Tente novamente."
            keyboard = [[InlineKeyboardButton("💳 Nova Recarga", callback_data="nova_recarga")]]
            
        else:
            mensagem = f"📊 Status: {status}"
            keyboard = [[InlineKeyboardButton("🔄 Verificar", callback_data=f"ver_{mp_id}")]]
        
        await query.edit_message_text(
            mensagem,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        print(f"❌ Erro verificação: {e}")
        await query.edit_message_text(
            "❌ Erro ao verificar. Tente novamente.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Tentar Novamente", callback_data=f"ver_{mp_id}")
            ]])
        )

async def nova_recarga(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Volta pro menu de recarga"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("💵 R$ 10", callback_data="pix_10")],
        [InlineKeyboardButton("💵 R$ 50", callback_data="pix_50")],
        [InlineKeyboardButton("💵 R$ 100", callback_data="pix_100")],
        [InlineKeyboardButton("💵 R$ 200", callback_data="pix_200")],
    ]
    
    await query.edit_message_text(
        "💳 *Nova Recarga PIX*\n\nEscolha o valor:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

# ============ INICIAR BOT ============

async def main():
    """Função principal"""
    print("=" * 40)
    print("🤖 Iniciando Bot PIX...")
    print("=" * 40)
    
    # Criar aplicação
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Adicionar handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(gerar_pix, pattern="^pix_"))
    app.add_handler(CallbackQueryHandler(verificar_pagamento, pattern="^ver_"))
    app.add_handler(CallbackQueryHandler(nova_recarga, pattern="^nova_recarga"))
    
    print("✅ Handlers configurados!")
    print("✅ Bot pronto para receber mensagens!")
    print("=" * 40)
    
    # Iniciar
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    # Manter rodando
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
