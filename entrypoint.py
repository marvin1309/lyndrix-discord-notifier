import requests
from datetime import datetime
from nicegui import ui
from core.api import ModuleManifest
from ui.theme import UIStyles

# ==========================================
# 1. MANIFEST: Identifikation & Rechte
# ==========================================
manifest = ModuleManifest(
    id="lyndrix.plugin.discord",
    name="Discord Notifier",
    version="0.0.4",
    description="Sendet System-Events und Status-Updates an Discord.",
    author="Lyndrix",
    icon="notifications_active",
    type="PLUGIN",
    min_core_version="1.0.0",
    auto_enable_on_install=False,
    repo_url="https://github.com/marvin1309/lyndrix-discord-notifier",
    permissions={
        "subscribe": ["change_requested", "system:boot_complete", "notification:outbound"],
        "emit": []
    }
)

# Globaler State für das Plugin (in Memory)
plugin_state = {
    "notifications_sent": 0
}

# ==========================================
# 2. LOGIK: Der API Client
# ==========================================
def send_webhook(ctx, webhook_url: str, bot_name: str, entity: str, action: str, payload: dict):
    embed_color = 5763719 if action == "CREATE" else 16753920 
    embed_fields = []
    
    for key, value in payload.items():
        if value != "" and value is not None:
            str_val = str(value)
            if len(str_val) > 100: str_val = str_val[:97] + "..."
            embed_fields.append({"name": str(key).capitalize(), "value": f"`{str_val}`", "inline": True})
            
    embed_fields = embed_fields[:25] # Discord Limit

    discord_msg = {
        "username": bot_name,
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/3256/3256013.png", 
        "embeds": [{
            "title": f"🚀 {entity} Event ausgelöst!",
            "description": f"Ein **{action}** Vorgang wurde registriert.\nDetails:",
            "color": embed_color,
            "fields": embed_fields,
            "footer": {"text": "Lyndrix Plugin Engine"},
            "timestamp": datetime.utcnow().isoformat()
        }]
    }
    
    try:
        response = requests.post(webhook_url, json=discord_msg, timeout=3)
        if response.status_code == 204:
            plugin_state["notifications_sent"] += 1
            ctx.log.info("SUCCESS: Embed sent to Discord.")
            return True
        else:
            ctx.log.warning(f"WARNING: Unexpected Discord status: {response.status_code}")
            return False
    except Exception as e:
        ctx.log.error(f"ERROR: Failed to send to Discord: {e}", exc_info=True)
        return False

def send_notification_webhook(ctx, webhook_url: str, bot_name: str, notif: dict):
    """Tailored specifically for the new Global Notification System payload."""
    type_colors = {
        "positive": 5763719,   # Emerald Green
        "negative": 15548997,  # Red
        "warning": 16753920,   # Amber/Yellow
        "info": 3447003        # Slate Blue
    }
    embed_color = type_colors.get(notif.get("type", "info"), 3447003)

    discord_msg = {
        "username": bot_name,
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/3256/3256013.png", 
        "embeds": [{
            "title": f"🔔 {notif.get('title', 'System Notification')}",
            "description": notif.get("message", "No content provided."),
            "color": embed_color,
            "footer": {"text": "Lyndrix Notification Engine"},
            "timestamp": datetime.utcnow().isoformat()
        }]
    }
    
    try:
        response = requests.post(webhook_url, json=discord_msg, timeout=3)
        if response.status_code == 204:
            plugin_state["notifications_sent"] += 1
            ctx.log.info(f"SUCCESS: Notification '{notif.get('title')}' sent to Discord.")
        else:
            ctx.log.warning(f"WARNING: Unexpected Discord status: {response.status_code}")
    except Exception as e:
        ctx.log.error(f"ERROR: Failed to send notification to Discord: {e}", exc_info=True)

# ==========================================
# 3. UI: Settings Tab (Wird später in globale Settings integriert)
# ==========================================
def render_settings_ui(ctx):
    """
    Diese Funktion baut die UI auf. Später ruft das globale Settings-Modul
    diese Funktion auf, wenn man auf den Tab 'Discord' klickt.
    """
    # Dummy-Einstellungen (Später aus der Datenbank laden)
    current_state = {"enabled": True, "bot_name": "Lyndrix Event Broker"}
    vault_state = {"webhook_url": ctx.get_secret("webhook_url") or ""}

    def apply_save():
        # TODO: 'enabled' und 'bot_name' in DB speichern (Phase 4.1)
        
        # Webhook im isolierten Plugin-Vault-Pfad speichern!
        if vault_state["webhook_url"]:
            success = ctx.set_secret("webhook_url", vault_state["webhook_url"])
            if success:
                ui.notify('Webhook sicher im Vault gespeichert!', type='positive')
            else:
                ui.notify('Fehler beim Speichern im Vault', type='negative')

    with ui.column().classes('w-full gap-4 pt-2'):

        with ui.card().classes(f'{UIStyles.CARD_GLASS} w-full').style('padding: 0; flex-wrap: nowrap'):
            ui.element('div').classes('h-1 w-full bg-gradient-to-r from-indigo-400 via-violet-400 to-purple-400')
            with ui.column().classes('w-full flex-grow p-5 gap-4'):
                with ui.row().classes('items-center gap-2 mb-1'):
                    ui.icon('notifications_active', size='18px').classes('text-indigo-400')
                    ui.label('Benachrichtigungen').classes('text-sm font-bold uppercase tracking-widest text-slate-300')
                ui.label('Konfiguration für System-Benachrichtigungen.').classes(UIStyles.TEXT_MUTED)
                with ui.row().classes('w-full items-center gap-4'):
                    ui.switch('Benachrichtigungen aktivieren').bind_value(current_state, 'enabled').props('color=primary')
                    ui.input('Bot Name').bind_value(current_state, 'bot_name').classes('flex-grow').props('outlined dense')

        with ui.card().classes(f'{UIStyles.CARD_GLASS} w-full').style('padding: 0; flex-wrap: nowrap'):
            ui.element('div').classes('h-1 w-full bg-gradient-to-r from-sky-400 via-cyan-400 to-teal-400')
            with ui.column().classes('w-full flex-grow p-5 gap-4'):
                with ui.row().classes('items-center gap-2 mb-1'):
                    ui.icon('webhook', size='18px').classes('text-sky-400')
                    ui.label('Webhook Konfiguration').classes('text-sm font-bold uppercase tracking-widest text-slate-300')
                # ACHTUNG: Hier wird der Webhook angezeigt, wenn er im Vault existiert
                ui.input('Discord Webhook URL (Vault)').bind_value(vault_state, 'webhook_url').classes('w-full').props('outlined dense type=password')
                with ui.row().classes('w-full justify-end mt-2'):
                    ui.button('Speichern', on_click=apply_save, icon='save', color='primary').props('unelevated rounded size=sm')

# ==========================================
# 4. SETUP: Das Herzstück des Plugins
# ==========================================
def setup(ctx):
    ctx.log.info("STARTUP: Plugin booting...")

    # Handler für Änderungen (Change Manager)
    @ctx.subscribe('change_requested')
    async def on_change(data):
        webhook_url = ctx.get_secret("webhook_url")
        if not webhook_url: return
        send_webhook(ctx, webhook_url, "Lyndrix Broker", data.get('entity_type', 'System'), data.get('action', 'UPDATE'), data.get('payload', {}))

    # NEU: Handler für erfolgreichen Systemstart
    @ctx.subscribe('system:boot_complete')
    async def on_boot_complete(payload):
        ctx.log.info("EVENT: Boot event received. Sending status to Discord...")
        webhook_url = ctx.get_secret("webhook_url")
        if not webhook_url: 
            ctx.log.warning("SKIP: Boot notification skipped: No webhook.")
            return
        
        # Wir nutzen die bestehende send_webhook Funktion
        send_webhook(
            ctx=ctx,
            webhook_url=webhook_url,
            bot_name="Lyndrix System",
            entity="Core Engine",
            action="STARTUP",
            payload={
                "status": "Online",
                "message": "Alle Kernsysteme erfolgreich hochgefahren.",
                "zeitpunkt": datetime.now().strftime("%H:%M:%S")
            }
        )
        
    # NEU: Zentraler Notification Handler
    @ctx.subscribe('notification:outbound')
    async def on_notification(payload):
        webhook_url = ctx.get_secret("webhook_url")
        if not webhook_url: return
        send_notification_webhook(ctx, webhook_url, "Lyndrix Notifier", payload)
        
    ctx.log.info("SUCCESS: Connected to Event Bus.")