# ====================================
# KinoBot — O'zbek tili (uz)
# ====================================

# ── Umumiy ──────────────────────────
btn-cancel = ❌ Bekor qilish
btn-back = ◀️ Ortga
btn-yes = ✅ Ha
btn-no = ❌ Yo'q
btn-close = 🔒 Yopish
btn-refresh = 🔄 Yangilash

# ── Start / Salomlashish ─────────────
welcome =
    👋 Salom, <b>{ $name }</b>!

    🎬 <b>KinoBot</b>ga xush kelibsiz!

    Bu bot orqali siz:
    🎥 Kino kodini kiritib istalgan kinoni olishingiz
    🔍 Kino nomi bo'yicha qidirishingiz mumkin!

    📌 <b>Qanday foydalanish:</b>
    • Kino kodini yuboring (masalan: <code>1234</code>) — kino darhol keladi
    • Yoki <b>🔍 Qidirish</b> tugmasini bosib nom bo'yicha izlang

    ❓ Yordam kerakmi? /help yozing

# ── Yordam ──────────────────────────
help =
    ℹ️ <b>KinoBot — Qo'llanma</b>

    🔢 <b>Kino kodini yuboring:</b>
    Kanalda e'lon qilingan kino kodini (masalan <code>1234</code>) to'g'ridan-to'g'ri yuboring — kino darhol yuboriladi.

    🔍 <b>Nom bo'yicha qidirish:</b>
    🔍 Qidirish tugmasini bosing yoki /search yozing, so'ng kino nomini kiriting.

    📌 <b>Buyruqlar:</b>
    /start — Botni qayta boshlash
    /search — Kino qidirish
    /help — Shu yordam

# ── Noma'lum xabar ──────────────────
unknown-command =
    ❓ Bunday buyruq mavjud emas.

    📌 Mavjud buyruqlar:
    /start — Botni boshlash
    /search — Kino qidirish
    /help — Yordam

unknown-message = 💡 Kino kodini yuboring (masalan: <code>1234</code>) yoki <b>🔍 Qidirish</b> tugmasini bosing.

# ── Obuna ───────────────────────────
subscription-required =
    🔒 <b>Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:</b>

subscribe-btn = 📢 { $title }
check-subscription-btn = ✅ Obuna bo'ldim, tekshir!

subscription-ok = ✅ Rahmat! Endi botdan foydalanishingiz mumkin.
subscription-fail =
    ❌ Siz hali barcha kanallarga obuna bo'lmadingiz.

    Quyidagi kanallarga obuna bo'ling va qayta tekshiring:

# ── Kino qidirish ───────────────────
search-prompt =
    🔍 <b>Qidiruv</b>

    Kino nomini yozing (masalan: <code>Inception</code>)
    yoki kino kodini yozing (masalan: <code>1234</code>):
search-no-results = 😔 <b>"{ $query }"</b> bo'yicha hech narsa topilmadi.
search-results-header = 🎬 <b>"{ $query }"</b> bo'yicha natijalar:
search-result-item = { $num }. <b>{ $title }</b> ({ $year }) — kod: <code>{ $code }</code>
search-select-prompt = ⬇️ Kino kodini yuboring yoki ro'yxatdan tanlang:
search-cancelled = ❌ Qidiruv bekor qilindi.

btn-random = 🎲 Tasodifiy
btn-popular = 🔥 Mashhur
btn-back-to-results = ◀️ Natijalarga qaytish
no-movies-available = 😔 Hozircha kinolar mavjud emas.
popular-movies-header = 🔥 <b>Eng mashhur kinolar:</b>

movie-not-found = ❌ <b>{ $code }</b> kodli kino topilmadi.

# ── Kino ma'lumoti ──────────────────
movie-info =
    🎬 <b>{ $title }</b>
    { $year ->
        [0] 
        *[other] 📅 Yil: <b>{ $year }</b>
    }
    { $duration ->
        [0] 
        *[other] ⏱ Davomiyligi: <b>{ $duration } daqiqa</b>
    }
    { $country ->
        [""] 
        *[other] 🌍 Mamlakat: <b>{ $country }</b>
    }
    { $genres ->
        [""] 
        *[other] 🎭 Janr: <b>{ $genres }</b>
    }
    { $lang_type ->
        [""] 
        *[other] 🔊 Til: <b>{ $lang_type }</b>
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

    👁 Ko'rilgan: <b>{ $views } marta</b>

# ── Xatolar ─────────────────────────
error-general = ❌ Xatolik yuz berdi. Qayta urinib ko'ring.
error-banned =
    🚫 Siz ban qilindingiz.
    { $reason ->
        [""] 
        *[other] Sabab: <i>{ $reason }</i>
    }
user-not-found = ❌ Foydalanuvchi topilmadi.

# ── Admin panel ─────────────────────
admin-panel =
    🎛 <b>Admin Panel</b>

    👤 Admin: <b>{ $name }</b>
    🏷 Rol: <b>{ $role }</b>

btn-admin-movies = 🎬 Kinolar
btn-admin-channels = 📢 Kanallar
btn-admin-admins = 👮 Adminlar
btn-admin-broadcast = 📣 Broadcast
btn-admin-stats = 📊 Statistika
btn-admin-sync = 🔄 Sync

access-denied = 🚫 Sizda bu amalni bajarish huquqi yo'q.

# ── Forward handler ─────────────────
movie-added = ✅ Yangi kino qo'shildi
movie-updated = 🔄 Kino yangilandi
forward-no-caption = ❌ Caption topilmadi. Kino ma'lumotlari caption'da bo'lishi kerak.
forward-no-code = ❌ Kino kodi topilmadi. Caption formatini tekshiring (#KOD_1234).

# ── Sync ────────────────────────────
sync-started =
    🔄 <b>Sync boshlandi.</b>

    Kino kanalidan xabarlar tekshirilmoqda...
    Bu jarayon bir necha daqiqa olishi mumkin.

    ⚠️ Admin chatida xabarlar bir zumga ko'rinib, avtomatik o'chiriladi.

sync-done =
    ✅ <b>Sync yakunlandi!</b>

    ➕ Yangi: <b>{ $added }</b>
    🔄 Yangilangan: <b>{ $updated }</b>
    ⏭ O'tkazilgan: <b>{ $skipped }</b>
    ⏱ Vaqt: <b>{ $duration } soniya</b>

sync-failed = ❌ Sync xatolik bilan tugadi: <code>{ $error }</code>
sync-already-running = ⏳ Sync allaqachon ishlayapti, kuting...

# ── Kanallar ────────────────────────
channels-list = 📢 <b>Majburiy kanallar ro'yxati:</b>
channel-add-prompt = Kanal username yoki ID sini yuboring (masalan: @mychannel yoki -1001234567890):
channel-added = ✅ <b>{ $title }</b> kanali qo'shildi.
channel-removed = ✅ Kanal o'chirildi.
channel-not-found = ❌ Kanal topilmadi.
channel-already-exists = ⚠️ Bu kanal allaqachon ro'yxatda bor.
channel-bot-not-admin = ❌ Bot bu kanalda admin emas. Avval botni kanalga admin qiling.

btn-channel-remove = 🗑 O'chirish
btn-channel-add = ➕ Kanal qo'shish

# ── Adminlar ────────────────────────
admins-list = 👮 <b>Adminlar ro'yxati:</b>
admin-add-prompt = Admin qilmoqchi bo'lgan foydalanuvchining Telegram ID sini yuboring:
admin-added = ✅ <b>{ $name }</b> admin qilindi.
admin-removed = ✅ Admin huquqi olib tashlandi.
admin-not-found = ❌ Admin topilmadi.
admin-already-exists = ⚠️ Bu foydalanuvchi allaqachon admin.
admin-cannot-remove-super = 🚫 Super adminni o'chirib bo'lmaydi.

# ── Broadcast ───────────────────────
broadcast-choose-target = 📣 <b>Broadcast maqsadini tanlang:</b>
btn-target-all = 👥 Barcha foydalanuvchilar
btn-target-active-7d = ✅ Faol (7 kun)
btn-target-active-30d = ✅ Faol (30 kun)
btn-target-lang-uz = 🇺🇿 O'zbeklar
btn-target-lang-ru = 🇷🇺 Ruslar
btn-target-lang-en = 🇺🇸 Inglizlar

broadcast-send-message = ✉️ Yubormoqchi bo'lgan xabarni yuboring (matn, rasm, video):
broadcast-preview =
    👁 <b>Preview:</b>

    📊 Maqsad: <b>{ $target }</b>
    👥 Taxminiy: <b>{ $count } foydalanuvchi</b>

    Yuborishlari mumkinmi?

broadcast-started = 📣 Broadcast boshlandi. <b>{ $total }</b> ta xabar yuboriladi...
broadcast-progress = ⏳ <b>{ $sent }/{ $total }</b> yuborildi...
broadcast-done =
    ✅ <b>Broadcast yakunlandi!</b>

    📤 Yuborildi: <b>{ $sent }</b>
    ❌ Xato: <b>{ $failed }</b>
    ⏱ Vaqt: <b>{ $duration } soniya</b>

# ── Statistika ──────────────────────
stats =
    📊 <b>Bot Statistikasi</b>

    👤 <b>Foydalanuvchilar:</b>
    ├ Jami: <b>{ $total_users }</b>
    ├ Bugun yangi: <b>{ $today_users }</b>
    ├ Hafta yangi: <b>{ $week_users }</b>
    ├ Oy yangi: <b>{ $month_users }</b>
    ├ Faol (7 kun): <b>{ $active_7d }</b>
    ├ Faol (30 kun): <b>{ $active_30d }</b>
    └ Banlangan: <b>{ $banned }</b>

    🎬 <b>Kinolar:</b>
    ├ Jami: <b>{ $total_movies }</b>
    └ Jami ko'rishlar: <b>{ $total_views }</b>

    🌐 <b>Tillar bo'yicha:</b>
    ├ 🇺🇿 O'zbek: <b>{ $lang_uz }</b>
    ├ 🇷🇺 Rus: <b>{ $lang_ru }</b>
    └ 🇺🇸 Ingliz: <b>{ $lang_en }</b>

# ── Moderatsiya ─────────────────────
ban-prompt = Ban qilmoqchi bo'lgan foydalanuvchining ID sini va sababini yuboring:

    Formatı: <code>ID | Sabab</code>
    Masalan: <code>123456789 | Spam</code>

ban-success =
    🚫 <b>{ $name }</b> ban qilindi.
    Sabab: <i>{ $reason }</i>

unban-prompt = Unban qilmoqchi bo'lgan foydalanuvchi ID sini yuboring:
unban-success = ✅ <b>{ $name }</b> unban qilindi.
unban-not-banned = ⚠️ Bu foydalanuvchi banlanmagan.

user-info =
    👤 <b>Foydalanuvchi ma'lumoti:</b>

    🆔 ID: <code>{ $telegram_id }</code>
    👤 Ism: <b>{ $name }</b>
    📛 Username: { $username }
    🌐 Til: <b>{ $language }</b>
    📅 Ro'yxatdan o'tgan: <b>{ $registered }</b>
    🕐 Oxirgi faollik: <b>{ $last_active }</b>
    🚫 Ban: <b>{ $is_banned }</b>
    { $ban_reason ->
        [""] 
        *[other] 📝 Ban sababi: <i>{ $ban_reason }</i>
    }
