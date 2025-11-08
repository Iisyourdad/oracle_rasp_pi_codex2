# admin.py
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import Group
from .models import HomePage, Recipe, Ingredient, Instruction

# --- ENABLE GROUPS IN ADMIN ---
# If you previously unregistered it, register it back:
try:
    admin.site.unregister(Group)   # no-op if not registered
except admin.sites.NotRegistered:
    pass
admin.site.register(Group, GroupAdmin)  # <-- brings back Auth → Groups

# (Optional) ensure the default User admin shows Groups + Permissions nicely
User = get_user_model()
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

@admin.register(User)
class MyUserAdmin(UserAdmin):
    # keep default fieldsets but ensure these fields appear with dual selector UI
    filter_horizontal = ("groups", "user_permissions")

# --- your existing admins ---
admin.site.site_header = "Westbrook Recipes Admin"
admin.site.site_title = "Westbrook Recipes"
admin.site.index_title = "Welcome to Westbrook Recipes"

@admin.register(HomePage)
class HomePageAdmin(admin.ModelAdmin):
    list_display = ("title", "background_image")

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    exclude = ("ingredients",)
    list_display = ("title", "meal_type", "display_favorites")
    list_filter = ("meal_type",)
    filter_horizontal = ("favorites",)

    def display_favorites(self, obj):
        return ", ".join(u.username for u in obj.favorites.all())
    display_favorites.short_description = "Favorites"

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("name",)

@admin.register(Instruction)
class InstructionAdmin(admin.ModelAdmin):
    list_display = ("title", "created_at")


#sessions

from django.contrib import admin
from django.contrib.sessions.models import Session

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("session_key", "expire_date", "decoded")
    readonly_fields = ("session_key", "expire_date", "decoded")
    search_fields = ("session_key",)

    def decoded(self, obj):
        return obj.get_decoded()


#admin change history

from django.contrib.admin.models import LogEntry
@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ("action_time", "user", "content_type", "object_repr", "action_flag")
    list_filter = ("user", "content_type", "action_flag")
    date_hierarchy = "action_time"
    search_fields = ("object_repr", "change_message")



