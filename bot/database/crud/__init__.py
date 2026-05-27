from bot.database.crud.user import (
    get_user,
    get_or_create_user,
    update_user_language,
    update_last_active,
    ban_user,
    unban_user,
    get_user_language,
)
from bot.database.crud.movie import (
    get_movie_by_code,
    search_movies,
    upsert_movie,
    delete_movie,
    record_view,
    get_movies_paginated,
    get_top_movies,
)
from bot.database.crud.channel import (
    get_active_channels,
    get_channel_by_id,
    add_channel,
    remove_channel,
    get_all_channels,
)
from bot.database.crud.admin import (
    get_admin_by_telegram_id,
    get_all_admins,
    add_admin,
    remove_admin,
    is_admin,
    update_admin_role,
)
from bot.database.crud.analytics import get_full_stats

__all__ = [
    # User
    "get_user", "get_or_create_user", "update_user_language",
    "update_last_active", "ban_user", "unban_user", "get_user_language",
    # Movie
    "get_movie_by_code", "search_movies", "upsert_movie", "delete_movie",
    "record_view", "get_movies_paginated", "get_top_movies",
    # Channel
    "get_active_channels", "get_channel_by_id", "add_channel",
    "remove_channel", "get_all_channels",
    # Admin
    "get_admin_by_telegram_id", "get_all_admins", "add_admin",
    "remove_admin", "is_admin", "update_admin_role",
    # Analytics
    "get_full_stats",
]
