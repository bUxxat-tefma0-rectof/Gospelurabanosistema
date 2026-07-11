import mercadopago
import base64
from io import BytesIO
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode
from dotenv import load_dotenv
import os
import asyncio

load_dotenv()

# Configurações
BOT_TOKEN = os.getenv("BOT_TOKEN")
sdk = mercadopago.SDK(os.getenv("MERCADO_PAGO_TOKEN"))

# Armazenamento temporário
pagamentos = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu principal"""
    keyboard = [
        [InlineKeyboardButton("💵 R$ 10", callback_data="pix_10")],
        [InlineKeyboardButton("💵 R$ 50", callback_data="pix_50")],
        [InlineKeyboardButton("💵 R$ 100", callback_data="pix_100")],
        [InlineKeyboardButton("💵 R$ 200", callback_data="pix_200")],
    ]
    
    await update.message.reply_text(
        "💳 *Recarga PIX - Teste*\nEscolha o valor:",
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
        resultado = sdk.payment().create({
            "transaction_amount": valor,
            "description": f"Recarga R$ {valor}",
            "payment_method_id": "pix",
            "payer": {"email": f"teste{user.id}@email.com"},
            "date_of_expiration": (datetime.utcnow() + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%S.000-03:00")
        })
        
        pagamento = resultado["response"]
        mp_id = pagamento["id"]
        qr_base64 = pagamento["point_of_interaction"]["transaction_data"]["qr_code_base64"]
        copia_cola = pagamento["point_of_interaction"]["transaction_data"]["qr_code"]
        
        pagamentos[mp_id] = {"user_id": user.id, "valor": valor, "status": "pending"}
        
        qr_image = base64.b64decode(qr_base64)
        
        keyboard = [[InlineKeyboardButton("🔄 Verificar Pagamento", callback_data=f"ver_{mp_id}")]]
        
        await query.message.reply_photo(
            BytesIO(qr_image),
            caption=f"📱 *PIX R$ {valor:.2f}*\n\n"
                   f"*Copia e Cola:*\n`{copia_cola}`\n\n"
                   f"⏰ Expira em 30 min\n"
                   f"🆔 `{mp_id}`",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        
        await query.message.delete()
        print(f"✅ PIX gerado: {mp_id} - R${valor}")
        
    except Exception as e:
        await query.edit_message_text(f"❌ Erro: {e}")

async def verificar_pix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verifica status do pagamento"""
    query = update.callback_query
    await query.answer()
    
    mp_id = query.data.replace("ver_", "")
    
    try:
        resultado = sdk.payment().get(mp_id)
        status = resultado["response"]["status"]
        
        if status == "approved":
            pagamentos[mp_id]["status"] = "approved"
            texto = "✅ *PAGAMENTO APROVADO!*\n🎉 Recarga realizada!"
        elif status == "pending":
            texto = "⏳ Aguardando pagamento..."
        else:
            texto = f"❌ Status: {status}"
        
        keyboard = [[InlineKeyboardButton("🔄 Verificar Novamente", callback_data=f"ver_{mp_id}")]]
        
        await query.edit_message_text(
            texto,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        await query.edit_message_text(f"❌ Erro: {e}")

async def main():
    """Inicia o bot"""
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(gerar_pix, pattern="^pix_"))
    app.add_handler(CallbackQueryHandler(verificar_pix, pattern="^ver_"))
    
    print("🤖 Bot iniciado!")
    
    # Iniciar polling
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    # Manter rodando
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
