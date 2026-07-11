import mercadopago
import base64
from io import BytesIO
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

BOT_TOKEN = "8603436205:AAGxsylTMG_4vd3madNaEaCh7sHu0-uKxio"
MERCADO_PAGO_TOKEN = "APP_USR-2096088157710260-021219-167b045d03f4904a28401b79190d54eb-2069324095"

sdk = mercadopago.SDK(MERCADO_PAGO_TOKEN)

async def recarregar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        valor = float(context.args[0])
    except:
        await update.message.reply_text("❌ Use: /recarregar VALOR\nExemplo: /recarregar 10")
        return
    
    try:
        resultado = sdk.payment().create({
            "transaction_amount": valor,
            "description": f"Recarga R$ {valor:.2f}",
            "payment_method_id": "pix",
            "payer": {"email": "teste@email.com"},
            "date_of_expiration": (datetime.utcnow() + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%S.000-03:00")
        })
        
        pagamento = resultado["response"]
        qr_base64 = pagamento["point_of_interaction"]["transaction_data"]["qr_code_base64"]
        copia_cola = pagamento["point_of_interaction"]["transaction_data"]["qr_code"]
        qr_image = base64.b64decode(qr_base64)
        
        await update.message.reply_photo(
            BytesIO(qr_image),
            caption=f"📱 *PIX R$ {valor:.2f}*\n\n`{copia_cola}`",
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Erro: {e}")

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("recarregar", recarregar))
print("🤖 Bot rodando...")
app.run_polling()
