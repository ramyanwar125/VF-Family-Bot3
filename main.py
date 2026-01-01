import aiohttp
import asyncio
import json
import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# --- إعدادات البوت ---
TOKEN = '8304738811:AAGplcj8YkZcmaY32zNifkraNWSLU5MWrgI'

# إعداد التنبيهات لرؤية ما يحدث في الخلفية
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- الثوابت والعناوين ---
AUTH_URL = 'https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token'
WEB_API_URL = "https://web.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"
MOBILE_API_URL = "https://mobile.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"
ACCEPT_INVITATION_URL = "https://mobile.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"
REMOVE_MEMBER_URL = "https://web.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"

CLIENT_ID = 'ana-vodafone-app'
CLIENT_SECRET = '95fd95fb-7489-4958-8ae6-d31a525cd20a'
USER_AGENT_MOBILE = 'VodafoneEG/5.5.1 (iPhone; iOS 16.6; Scale/3.00)'
USER_AGENT_ANDROID = "okhttp/4.11.0"

# --- الدوال التقنية (معدلة لتعمل مع البوت) ---

async def authenticate_vodafone_async(session, username, password, is_mobile_agent=False):
    data = {
        'grant_type': 'password',
        'username': username,
        'password': password,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': USER_AGENT_MOBILE if is_mobile_agent else "Mozilla/5.0"
    }
    try:
        async with session.post(AUTH_URL, data=data, headers=headers, timeout=30) as response:
            if response.status == 200:
                res = await response.json()
                return res.get('access_token')
    except:
        return None

async def send_web_request_async(session, access_token, owner_number, member_number, quota_value):
    payload = json.dumps({
        "name": "FlexFamily", 
        "type": "SendInvitation", 
        "category": [{"value": "523", "listHierarchyId": "PackageID"}, {"value": "47", "listHierarchyId": "TemplateID"}], 
        "parts": { 
            "member": [{"id": [{"value": owner_number, "schemeName": "MSISDN"}], "type": "Owner"},
                       {"id": [{"value": member_number, "schemeName": "MSISDN"}], "type": "Member"}], 
            "characteristicsValue": {"characteristicsValue": [{"characteristicName": "quotaDist1", "value": str(quota_value), "type": "percentage"}]}
        }
    })
    headers = {
        'Content-Type': "application/json",
        'Authorization': f"Bearer {access_token}", 
        'msisdn': owner_number, 
        'clientId': "WebsiteConsumer"
    }
    async with session.post(WEB_API_URL, data=payload, headers=headers) as resp:
        return resp.status in [200, 201, 204]

async def accept_invitation_async(session, owner_number, member_number, member_password):
    access_token = await authenticate_vodafone_async(session, member_number, member_password, True)
    if not access_token: return False
    
    headers = {"Authorization": f"Bearer {access_token}", "msisdn": member_number, "Content-Type": "application/json", "clientId": "AnaVodafoneAndroid"}
    data = {
        "category": [{"listHierarchyId": "TemplateID", "value": "47"}],
        "name": "FlexFamily",
        "parts": {"member": [{"id": [{"schemeName": "MSISDN", "value": owner_number}], "type": "Owner"},
                            {"id": [{"schemeName": "MSISDN", "value": member_number}], "type": "Member"}]},
        "type": "AcceptInvitation"
    }
    async with session.patch(ACCEPT_INVITATION_URL, headers=headers, json=data) as resp:
        return resp.status in [200, 201]

# --- وظائف البوت ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 **مرحباً بك في بوت فليكس فاميلي المطور!**\n\n"
        "أرسل البيانات بالصيغة التالية:\n"
        "`رقم_الأونر:باسورد_الأونر:رقم_العضو:باسورد_العضو:النسبة`\n\n"
        "💡 مثال: `01012345678:Pass123:01098765432:Pass456:40`",
        parse_mode='Markdown'
    )

async def process_flex(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = update.message.text.split(':')
        if len(data) != 5:
            await update.message.reply_text("⚠️ خطأ في التنسيق! تأكد من وجود 5 قيم مفصولة بـ :")
            return

        owner_num, owner_pass, member_num, member_pass, quota = data
        status_msg = await update.message.reply_text("⏳ جاري بدء العملية... جاري تحضير التوكنات.")

        async with aiohttp.ClientSession() as session:
            # 1. تسجيل الدخول
            token = await authenticate_vodafone_async(session, owner_num, owner_pass)
            if not token:
                await status_msg.edit_text("❌ فشل تسجيل دخول الأونر. تأكد من البيانات.")
                return

            # 2. إرسال الدعوة
            await status_msg.edit_text("📡 تم الحصول على التوكن. جاري إرسال الدعوة...")
            invitation_sent = await send_web_request_async(session, token, owner_num, member_num, quota)
            
            if invitation_sent:
                await status_msg.edit_text("✅ تم إرسال الدعوة بنجاح! جاري محاولة القبول من رقم العضو...")
                await asyncio.sleep(10) # انتظار بسيط للتأكد من وصولها للسيستم
                
                # 3. قبول الدعوة
                success = await accept_invitation_async(session, owner_num, member_num, member_pass)
                if success:
                    await status_msg.edit_text(f"🎉 **مبروك! تمت الإضافة بنجاح.**\n👥 العضو: {member_num}\n💰 الحصة: {quota}%")
                else:
                    await status_msg.edit_text("⚠️ أرسلت الدعوة ولكن فشل القبول التلقائي. حاول القبول يدوياً من تطبيق أنا فودافون.")
            else:
                await status_msg.edit_text("❌ فشل إرسال الدعوة. قد يكون الرقم مضافاً بالفعل أو هناك حظر مؤقت.")

    except Exception as e:
        await update.message.reply_text(f"💥 حدث خطأ غير متوقع: {str(e)}")

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), process_flex))
    
    print("البوت يعمل الآن... أرسل رسالة من تلجرام للبدء.")
    application.run_polling()
