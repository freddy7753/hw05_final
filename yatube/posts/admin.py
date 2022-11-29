from django.contrib import admin

from .models import Post, Group, Comment, Follow


class PostAdmin(admin.ModelAdmin):
    list_display = (
        'pk',
        'text',
        'pub_date',
        'author',
        'group',
        'image'
    )
    list_editable = ('group',)
    search_fields = ('text',)
    list_filter = ('pub_date',)
    empty_value_display = '-пусто-'


class CommentAdmin(admin.ModelAdmin):
    list_display = (
        'post',
        'text',
        'created',
        'author',
    )
    search_fields = ('created', 'author', 'post',)
    list_filter = ('author', 'created',)
    list_editable = ('text',)


class FollowAdmin(admin.ModelAdmin):
    list_display = ('user', 'author')


class GroupAdmin(admin.ModelAdmin):
    list_display = ('title', 'description', 'slug')
    list_editable = ('description', 'slug')
    list_filter = ('title',)
    search_fields = ('title', 'slug',)


admin.site.register(Post, PostAdmin)
admin.site.register(Group, GroupAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(Follow, FollowAdmin)
