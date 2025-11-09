# admin.py
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import Group
from django.conf import settings
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from pathlib import Path
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
    list_display = ("title", "user", "background_image")
    search_fields = ("title", "user__username")

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(user=request.user)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "user" and not request.user.is_superuser:
            kwargs["queryset"] = User.objects.filter(pk=request.user.pk)
            kwargs.setdefault("initial", request.user.pk)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            obj.user = request.user
        super().save_model(request, obj, form, change)

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


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".ico"}
DELETED_DIR_NAME = "_deleted_media"


def _is_within(child, parent):
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _resolve_under(base_dir, relative_path):
    candidate = (base_dir / relative_path).resolve()
    base_resolved = base_dir.resolve()
    candidate.relative_to(base_resolved)
    return candidate


def _gather_media_files(base_dir, scan_root, *, exclude=None, relative_to=None, url_prefix=None):
    relative_to = relative_to or base_dir
    url_prefix = url_prefix or settings.MEDIA_URL
    files = []
    if not scan_root.exists():
        return files
    for path in scan_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        if exclude and _is_within(path, exclude):
            continue
        rel_path = path.relative_to(relative_to)
        rel_posix = rel_path.as_posix()
        files.append({
            "name": path.name,
            "relative": rel_posix,
            "size": path.stat().st_size,
            "url": f"{url_prefix}{rel_posix}",
        })
    return sorted(files, key=lambda item: item["relative"])


def _soft_delete_file(base_dir, deleted_root, relative_path):
    target = _resolve_under(base_dir, relative_path)
    destination = (deleted_root / relative_path).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination_path = Path(destination)
    target.replace(destination_path)
    HomePage.objects.filter(background_image=relative_path).update(background_image="")
    return relative_path


def _restore_deleted_file(base_dir, deleted_root, relative_path):
    source = _resolve_under(deleted_root, relative_path)
    destination = (base_dir / relative_path).resolve()
    destination_path = Path(destination)
    if destination_path.exists():
        raise FileExistsError(f"Destination already exists: {relative_path}")
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    source.replace(destination_path)


def _purge_deleted_file(deleted_root, relative_path):
    source = _resolve_under(deleted_root, relative_path)
    source.unlink(missing_ok=True)


def media_library_view(request):
    base_dir = Path(settings.MEDIA_ROOT)
    base_dir.mkdir(parents=True, exist_ok=True)
    deleted_root = base_dir / DELETED_DIR_NAME
    deleted_root.mkdir(parents=True, exist_ok=True)
    available_dirs = sorted([
        p.name for p in base_dir.iterdir()
        if p.is_dir() and p.name != DELETED_DIR_NAME
    ])
    selected_dir = request.GET.get("dir") or request.POST.get("dir")
    if selected_dir not in available_dirs:
        selected_dir = None
    scan_root = base_dir / selected_dir if selected_dir else base_dir

    redirect_url = request.path
    if selected_dir:
        redirect_url = f"{redirect_url}?dir={selected_dir}"

    if request.method == "POST":
        rel_target = request.POST.get("target")
        action = request.POST.get("action", "delete")
        if not rel_target:
            messages.error(request, "No file selected.")
            return HttpResponseRedirect(redirect_url)
        try:
            if action == "delete":
                _soft_delete_file(base_dir, deleted_root, rel_target)
                messages.success(request, f"Moved {rel_target} to deleted images.")
            elif action == "restore":
                _restore_deleted_file(base_dir, deleted_root, rel_target)
                messages.success(request, f"Restored {rel_target}.")
            elif action == "purge":
                _purge_deleted_file(deleted_root, rel_target)
                messages.success(request, f"Permanently removed {rel_target}.")
            else:
                messages.error(request, "Unknown action.")
        except FileExistsError as exc:
            messages.error(request, str(exc))
        except ValueError:
            messages.error(request, "Invalid file path.")
        return HttpResponseRedirect(redirect_url)

    files = _gather_media_files(base_dir, scan_root, exclude=deleted_root)
    deleted_files = _gather_media_files(
        deleted_root,
        deleted_root,
        relative_to=deleted_root,
        url_prefix=f"{settings.MEDIA_URL}{DELETED_DIR_NAME}/"
    )
    context = admin.site.each_context(request)
    context.update({
        "title": "Media Library",
        "files": files,
        "deleted_files": deleted_files,
        "directories": available_dirs,
        "selected_dir": selected_dir,
        "media_root": base_dir,
    })
    return TemplateResponse(request, "admin/media_library.html", context)


def _media_library_urls(original_urls):
    def new_urls():
        custom = [
            path("media-library/", admin.site.admin_view(media_library_view), name="media-library"),
        ]
        return custom + original_urls()
    return new_urls


admin.site.get_urls = _media_library_urls(admin.site.get_urls)


_original_get_app_list = admin.site.get_app_list

def _media_app_list(request):
    app_list = list(_original_get_app_list(request))
    media_url = reverse("admin:media-library")
    media_entry = {
        "name": "Media",
        "app_label": "media_tools",
        "app_url": media_url,
        "has_module_perms": True,
        "models": [
            {
                "name": "Media Library",
                "object_name": "MediaLibrary",
                "perms": {"add": False, "change": True, "delete": False, "view": True},
                "admin_url": media_url,
                "view_only": True,
            }
        ],
    }
    if not any(app.get("app_label") == "media_tools" for app in app_list):
        app_list.append(media_entry)
    return app_list


admin.site.get_app_list = _media_app_list
