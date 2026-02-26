from django.contrib import admin

from .models import (
    Course,
    Enrollment,
    Instructor,
    Material,
    Module,
    Progress,
    Rating,
    ReadingMaterial,
    VideoMaterial,
)


class ModuleInline(admin.TabularInline):
    model = Module
    extra = 1
    show_change_link = True


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "category", "status", "course_start", "course_end", "created_at"]
    list_filter = ["status", "category", "course_start"]
    search_fields = ["title", "subtitle", "user__username"]
    date_hierarchy = "created_at"
    inlines = [ModuleInline]
    fieldsets = [
        (None, {"fields": ["user", "title", "subtitle", "category", "description", "cover_img"]}),
        ("Schedule", {"fields": ["registration_start", "registration_end", "course_start", "course_end"]}),
        ("Status", {"fields": ["status"]}),
    ]


class MaterialInline(admin.TabularInline):
    model = Material
    extra = 1
    show_change_link = True


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ["name", "course"]
    search_fields = ["name", "course__title"]
    inlines = [MaterialInline]


class VideoMaterialInline(admin.StackedInline):
    model = VideoMaterial
    extra = 0
    can_delete = False


class ReadingMaterialInline(admin.StackedInline):
    model = ReadingMaterial
    extra = 0
    can_delete = False


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ["name", "module", "type", "due_date"]
    list_filter = ["type", "due_date"]
    search_fields = ["name", "module__name", "module__course__title"]
    inlines = [VideoMaterialInline, ReadingMaterialInline]


@admin.register(VideoMaterial)
class VideoMaterialAdmin(admin.ModelAdmin):
    list_display = ["title", "material", "uploaded_at"]
    search_fields = ["title", "material__name"]


@admin.register(ReadingMaterial)
class ReadingMaterialAdmin(admin.ModelAdmin):
    list_display = ["title", "material", "uploaded_at"]
    search_fields = ["title", "material__name"]