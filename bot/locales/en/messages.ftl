# ====================================
# KinoBot — English (en)
# ====================================

# ── General ─────────────────────────
btn-cancel = ❌ Cancel
btn-back = ◀️ Back
btn-yes = ✅ Yes
btn-no = ❌ No
btn-close = 🔒 Close
btn-refresh = 🔄 Refresh

# ── Start / Welcome ──────────────────
welcome =
    👋 Hello, <b>{ $name }</b>!

    🎬 Welcome to <b>KinoBot</b>!

    With this bot you can:
    🎥 Get any movie by its code
    🔍 Search movies by title

    📌 <b>How to use:</b>
    • Send a movie code (e.g. <code>1234</code>) — the movie arrives instantly
    • Or tap <b>🔍 Search</b> to find by title

    ❓ Need help? Type /help

# ── Help ────────────────────────────
help =
    ℹ️ <b>KinoBot — Guide</b>

    🔢 <b>Send a movie code:</b>
    Send the code from the channel (e.g. <code>1234</code>) — the movie will be sent instantly.

    🔍 <b>Search by title:</b>
    Tap 🔍 Search or type /search, then enter a movie title.

    📌 <b>Commands:</b>
    /start — Restart the bot
    /search — Search for a movie
    /help — This guide

# ── Unknown message ──────────────────
unknown-command =
    ❓ This command does not exist.

    📌 Available commands:
    /start — Start the bot
    /search — Search for a movie
    /help — Help

unknown-message = 💡 Send a movie code (e.g. <code>1234</code>) or tap <b>🔍 Search</b>.

# ── Subscription ────────────────────
subscription-required =
    🔒 <b>To use the bot, please subscribe to the following channels:</b>

subscribe-btn = 📢 { $title }
check-subscription-btn = ✅ I've subscribed, check now!

subscription-ok = ✅ Thank you! You can now use the bot.
subscription-fail =
    ❌ You haven't subscribed to all channels yet.

    Please subscribe and check again:

# ── Movie Search ────────────────────
search-prompt =
    🔍 <b>Search</b>

    Enter a movie title (e.g. <code>Inception</code>)
    or movie code (e.g. <code>1234</code>):
search-no-results = 😔 No results found for <b>"{ $query }"</b>.
search-results-header = 🎬 <b>Results for "{ $query }":</b>
search-result-item = { $num }. <b>{ $title }</b> ({ $year }) — code: <code>{ $code }</code>
search-select-prompt = ⬇️ Send the movie code or select from the list:

movie-not-found = ❌ Movie with code <b>{ $code }</b> not found.

# ── Movie Info ──────────────────────
movie-info =
    🎬 <b>{ $title }</b>
    { $year ->
        [0] 
        *[other] 📅 Year: <b>{ $year }</b>
    }
    { $duration ->
        [0] 
        *[other] ⏱ Duration: <b>{ $duration } min</b>
    }
    { $country ->
        [""] 
        *[other] 🌍 Country: <b>{ $country }</b>
    }
    { $genres ->
        [""] 
        *[other] 🎭 Genre: <b>{ $genres }</b>
    }
    { $lang_type ->
        [""] 
        *[other] 🔊 Language: <b>{ $lang_type }</b>
    }
    { $imdb ->
        [0] 
        *[other] ⭐ IMDb: <b>{ $imdb }</b>
    }
    { $kinopoisk ->
        [0] 
        *[other] 🎯 Kinopoisk: <b>{ $kinopoisk }</b>
    }
    { $description ->
        [""] 
        *[other] 
            📝 <i>{ $description }</i>
    }

    👁 Views: <b>{ $views }</b>

# ── Errors ──────────────────────────
error-general = ❌ An error occurred. Please try again.
error-banned =
    🚫 You have been banned.
    { $reason ->
        [""] 
        *[other] Reason: <i>{ $reason }</i>
    }
user-not-found = ❌ User not found.

# ── Admin Panel ─────────────────────
admin-panel =
    🎛 <b>Admin Panel</b>

    👤 Admin: <b>{ $name }</b>
    🏷 Role: <b>{ $role }</b>

btn-admin-movies = 🎬 Movies
btn-admin-channels = 📢 Channels
btn-admin-admins = 👮 Admins
btn-admin-broadcast = 📣 Broadcast
btn-admin-stats = 📊 Statistics
btn-admin-sync = 🔄 Sync

access-denied = 🚫 You don't have permission to perform this action.

# ── Forward handler ─────────────────
movie-added = ✅ New movie added
movie-updated = 🔄 Movie updated
forward-no-caption = ❌ No caption found. Movie info must be in the caption.
forward-no-code = ❌ Movie code not found. Check the caption format (#KOD_1234).

# ── Sync ────────────────────────────
sync-started =
    🔄 <b>Sync started.</b>

    Scanning messages from the movie channel...
    This may take a few minutes.

    ⚠️ Messages will briefly appear in the admin chat and be automatically deleted.

sync-done =
    ✅ <b>Sync completed!</b>

    ➕ Added: <b>{ $added }</b>
    🔄 Updated: <b>{ $updated }</b>
    ⏭ Skipped: <b>{ $skipped }</b>
    ⏱ Time: <b>{ $duration } sec</b>

sync-failed = ❌ Sync failed with error: <code>{ $error }</code>
sync-already-running = ⏳ Sync is already running, please wait...

# ── Channels ────────────────────────
channels-list = 📢 <b>Mandatory channels list:</b>
channel-add-prompt = Send the channel username or ID (e.g. @mychannel or -1001234567890):
channel-added = ✅ Channel <b>{ $title }</b> added.
channel-removed = ✅ Channel removed.
channel-not-found = ❌ Channel not found.
channel-already-exists = ⚠️ This channel is already in the list.
channel-bot-not-admin = ❌ Bot is not an admin in this channel. Please add the bot as an admin first.

btn-channel-remove = 🗑 Remove
btn-channel-add = ➕ Add channel

# ── Admins ──────────────────────────
admins-list = 👮 <b>Admins list:</b>
admin-add-prompt = Send the Telegram ID of the user you want to make an admin:
admin-added = ✅ <b>{ $name }</b> has been made an admin.
admin-removed = ✅ Admin rights removed.
admin-not-found = ❌ Admin not found.
admin-already-exists = ⚠️ This user is already an admin.
admin-cannot-remove-super = 🚫 Cannot remove a super admin.

# ── Broadcast ───────────────────────
broadcast-choose-target = 📣 <b>Choose broadcast audience:</b>
btn-target-all = 👥 All users
btn-target-active-7d = ✅ Active (7 days)
btn-target-active-30d = ✅ Active (30 days)
btn-target-lang-uz = 🇺🇿 Uzbek speakers
btn-target-lang-ru = 🇷🇺 Russian speakers
btn-target-lang-en = 🇺🇸 English speakers

broadcast-send-message = ✉️ Send the message to broadcast (text, photo, video):
broadcast-preview =
    👁 <b>Preview:</b>

    📊 Target: <b>{ $target }</b>
    👥 Recipients: <b>{ $count }</b>

    Proceed with broadcast?

broadcast-started = 📣 Broadcast started. Sending <b>{ $total }</b> messages...
broadcast-progress = ⏳ <b>{ $sent }/{ $total }</b> sent...
broadcast-done =
    ✅ <b>Broadcast completed!</b>

    📤 Sent: <b>{ $sent }</b>
    ❌ Failed: <b>{ $failed }</b>
    ⏱ Time: <b>{ $duration } sec</b>

# ── Statistics ──────────────────────
stats =
    📊 <b>Bot Statistics</b>

    👤 <b>Users:</b>
    ├ Total: <b>{ $total_users }</b>
    ├ Today new: <b>{ $today_users }</b>
    ├ Week new: <b>{ $week_users }</b>
    ├ Month new: <b>{ $month_users }</b>
    ├ Active (7d): <b>{ $active_7d }</b>
    ├ Active (30d): <b>{ $active_30d }</b>
    └ Banned: <b>{ $banned }</b>

    🎬 <b>Movies:</b>
    ├ Total: <b>{ $total_movies }</b>
    └ Total views: <b>{ $total_views }</b>

    🌐 <b>By language:</b>
    ├ 🇺🇿 Uzbek: <b>{ $lang_uz }</b>
    ├ 🇷🇺 Russian: <b>{ $lang_ru }</b>
    └ 🇺🇸 English: <b>{ $lang_en }</b>

# ── Moderation ──────────────────────
ban-prompt = Send the user ID and ban reason:

    Format: <code>ID | Reason</code>
    Example: <code>123456789 | Spam</code>

ban-success =
    🚫 <b>{ $name }</b> has been banned.
    Reason: <i>{ $reason }</i>

unban-prompt = Send the user ID to unban:
unban-success = ✅ <b>{ $name }</b> has been unbanned.
unban-not-banned = ⚠️ This user is not banned.

user-info =
    👤 <b>User Information:</b>

    🆔 ID: <code>{ $telegram_id }</code>
    👤 Name: <b>{ $name }</b>
    📛 Username: { $username }
    🌐 Language: <b>{ $language }</b>
    📅 Registered: <b>{ $registered }</b>
    🕐 Last active: <b>{ $last_active }</b>
    🚫 Banned: <b>{ $is_banned }</b>
    { $ban_reason ->
        [""] 
        *[other] 📝 Ban reason: <i>{ $ban_reason }</i>
    }
