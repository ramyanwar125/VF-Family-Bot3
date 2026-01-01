import aiohttp
import asyncio
import json
import random
import os
from colorama import init, Fore, Style
import pyfiglet

# --- إعدادات تليجرام ---
# تم وضع التوكن الخاص بك هنا
TELEGRAM_TOKEN = "8304738811:AAGplcj8YkZcmaY32zNifkraNWSLU5MWrgI"
API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# --- تهيئة الألوان للمنصة ---
init(autoreset=True)
SUCCESS_COLOR = Style.BRIGHT + Fore.GREEN
ERROR_COLOR = Style.BRIGHT + Fore.RED
INFO_COLOR = Style.BRIGHT + Fore.BLUE

# --- الثوابت التقنية لفودافون ---
AUTH_URL = 'https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token'
WEB_API_URL = "https://web.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"
MOBILE_API_URL = "https://mobile.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"
ACCEPT_INVITATION_URL = "https://mobile.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"
REMOVE_MEMBER_URL = "https://web.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"

CLIENT_ID = 'ana-vodafone-app'
CLIENT_SECRET = '95fd95fb-7489-4958-8ae6-d31a525cd20a'
USER_AGENT_MOBILE = 'VodafoneEG/5.5.1 (iPhone; iOS 16.6; Scale/3.00)'
USER_AGENT_ANDROID = "okhttp/4.11.0"
USER_AGENTS_APPLE = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
]

# --- وظائف تليجرام المساعدة ---
async def send_telegram_message(chat_id, text):
    url = f"{API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            return await response.json()

# --- دوال فودافون (SIZER Core) ---

async def authenticate_vodafone_async(session, username, password, is_mobile_agent=False):
    data = {
        'grant_type': 'password', 'username': username, 'password': password,
        'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': USER_AGENT_MOBILE if is_mobile_agent else random.choice(USER_AGENTS_APPLE)
    }
    try:
        async with session.post(AUTH_URL, data=data, headers=headers, timeout=30) as response:
            if response.status == 200:
                res = await response.json()
                return res.get('access_token')
    except: return None

async def send_web_request_async(session, access_token, owner_number, member_number, quota_value):
    payload = json.dumps({
        "name": "FlexFamily", "type": "SendInvitation", 
        "category": [{"value": "523", "listHierarchyId": "PackageID"}, {"value": "47", "listHierarchyId": "TemplateID"}, {"value": "523", "listHierarchyId": "TierID"}, {"value": "percentage", "listHierarchyId": "familybehavior"}], 
        "parts": {"member": [{"id": [{"value": owner_number, "schemeName": "MSISDN"}], "type": "Owner"},{"id": [{"value": member_number, "schemeName": "MSISDN"}], "type": "Member"}], "characteristicsValue": {"characteristicsValue": [{"characteristicName": "quotaDist1", "value": str(quota_value), "type": "percentage"}]}}
    })
    headers = {'User-Agent': random.choice(USER_AGENTS_APPLE), 'Content-Type': "application/json", 'Authorization': f"Bearer {access_token}", 'msisdn': owner_number, 'clientId': "WebsiteConsumer", 'Origin': "https://web.vodafone.com.eg"}
    try:
        async with session.post(WEB_API_URL, data=payload, headers=headers, timeout=30) as response:
            return response.status in [200, 201, 204], response.status
    except: return False, 0

async def accept_invitation_async(session, owner_number, member_number, member_password):
    access_token = await authenticate_vodafone_async(session, member_number, member_password, is_mobile_agent=True)
    if not access_token: return False
    headers = {"Authorization": f"Bearer {access_token}", "msisdn": member_number, "clientId": "AnaVodafoneAndroid", "api-version": "v2", "Content-Type": "application/json"}
    data = {"category": [{"listHierarchyId": "TemplateID", "value": "47"}], "name": "FlexFamily", "parts": {"member": [{"id": [{"schemeName": "MSISDN", "value": owner_number}], "type": "Owner"},{"id": [{"schemeName": "MSISDN", "value": member_number}], "type": "Member"}]},"type": "AcceptInvitation"}
    try:
        async with session.patch(ACCEPT_INVITATION_URL, json=data, headers=headers, timeout=30) as response:
            return response.status in [200, 201]
    except: return False

async def remove_member_async(session, access_token, owner_number, member_number):
    payload = {"name": "FlexFamily", "type": "FamilyRemoveMember", "category": [{"value": "47", "listHierarchyId": "TemplateID"}], "parts": {"member": [{"id": [{"value": owner_number, "schemeName": "MSISDN"}], "type": "Owner"},{"id": [{"value": member_number, "schemeName": "MSISDN"}], "type": "Member"}],"characteristicsValue": {"characteristicsValue": [{"characteristicName": "Disconnect", "value": "0"},{"characteristicName": "LastMemberDeletion", "value": "1"}]}}}
    headers = {'Content-Type': "application/json", 'msisdn': owner_number, 'clientId': "WebsiteConsumer", 'Authorization': f"Bearer {access_token}"}
    try:
        async with session.patch(REMOVE_MEMBER_URL, json=payload, headers=headers, timeout=30) as response:
            return response.status in [200, 404]
    except: return False

# --- محرك التشغيل الرئيسي المرتبط بتليجرام ---
async def run_sizer_process(chat_id, settings):
    await send_telegram_message(chat_id, "🚀 *بدء عملية SIZER...*")
    
    async with aiohttp.ClientSession() as session:
        for attempt in range(1, settings["total_attempts"] + 1):
            await send_telegram_message(chat_id, f"🔄 جولة رقم {attempt}...")
            
            # محاولة جلب توكن الأونر
            token = await authenticate_vodafone_async(session, settings["owner_number"], settings["owner_password"])
            if not token:
                await send_telegram_message(chat_id, "❌ فشل تسجيل دخول الأونر.")
                return

            # إرسال الدعوة
            success, status = await send_web_request_async(session, token, settings["owner_number"], settings["member_number"], settings["quota_percentage"])
            
            if success:
                await send_telegram_message(chat_id, "✅ تم إرسال الدعوة بنجاح! جاري القبول...")
                await asyncio.sleep(15)
                if await accept_invitation_async(session, settings["owner_number"], settings["member_number"], settings["member_password"]):
                    await send_telegram_message(chat_id, f"🎉 *مبروك! تمت الإضافة بنجاح بقوة SIZER!*")
                    return
                else:
                    await send_telegram_message(chat_id, "⚠️ فشل قبول الدعوة، سأحاول مجدداً.")
            
            # تنظيف المحاولة الفاشلة
            await remove_member_async(session, token, settings["owner_number"], settings["member_number"])
            await asyncio.sleep(10)

        await send_telegram_message(chat_id, "💥 انتهت جميع المحاولات دون نجاح.")

# --- استقبال الرسائل من تليجرام (Long Polling) ---
async def main():
    print(Fore.CYAN + pyfiglet.figlet_format('SIZER BOT'))
    print(INFO_COLOR + "🤖 البوت يعمل الآن ويستقبل الأوامر...")
    
    offset = 0
    # إعدادات افتراضية (يفضل ضبطها في Render Environment Variables)
    settings = {
        "owner_number": os.getenv("OWNER_NUM", "010xxxxxxxx"),
        "owner_password": os.getenv("OWNER_PASS", "password"),
        "member_number": os.getenv("MEMBER_NUM", "010xxxxxxxx"),
        "member_password": os.getenv("MEMBER_PASS", "password"),
        "quota_percentage": "40",
        "total_attempts": 10
    }

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                updates_url = f"{API_URL}/getUpdates?offset={offset}&timeout=30"
                async with session.get(updates_url) as response:
                    updates = await response.json()
                    
                    for update in updates.get("result", []):
                        offset = update["update_id"] + 1
                        message = update.get("message", {})
                        chat_id = message.get("chat", {}).get("id")
                        text = message.get("text", "")

                        if text == "/start":
                            await send_telegram_message(chat_id, "👋 أهلاً بك في *SIZER Power*\nأرسل `/run` للبدء بالبيانات المسجلة.")
                        elif text == "/run":
                            asyncio.create_task(run_sizer_process(chat_id, settings))
            except Exception as e:
                print(f"Error: {e}")
                await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
