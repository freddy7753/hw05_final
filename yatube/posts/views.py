from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_page

from .forms import PostForm, CommentForm
from .models import Post, Group, Comment, Follow, User
from .utils import get_paginator_obj


@cache_page(20, key_prefix='index_page')
def index(request):
    post_list = Post.objects.select_related('author', 'group')
    page_obj = get_paginator_obj(post_list, request)
    return render(request, 'posts/index.html', {'page_obj': page_obj})


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    post_list = group.posts.select_related('group', 'author')
    page_obj = get_paginator_obj(post_list, request)
    return render(
        request,
        'posts/group_list.html',
        {'group': group, 'page_obj': page_obj}
    )


def profile(request, username):
    author = get_object_or_404(User, username=username)
    user_posts = author.posts.select_related('author', 'group')
    page_obj = get_paginator_obj(user_posts, request)
    following = (
        request.user.is_authenticated
        and request.user != author
        and request.user.follower.filter(
            author=author
        ).exists()
    )
    return render(
        request,
        'posts/profile.html',
        {'following': following, 'page_obj': page_obj, 'author': author}
    )


def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    comments = Comment.objects.filter(post=post)
    form = CommentForm(request.POST or None)
    return render(
        request,
        'posts/post_detail.html',
        {'post': post, 'form': form, 'comments': comments}
    )


@login_required
def post_create(request):
    user = get_object_or_404(User, id=request.user.pk)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None
    )
    if form.is_valid():
        new_post = form.save(commit=False)
        new_post.author = request.user
        new_post.save()
        return redirect(reverse('posts:profile', args=[user]))
    return render(request, 'posts/create_post.html', {'form': form})


def post_edit(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.user != post.author:
        return redirect(reverse('posts:post_detail', args=[post_id]))

    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if form.is_valid():
        form.save()
        return redirect(reverse('posts:post_detail', args=[post_id]))
    return render(
        request,
        'posts/create_post.html',
        {'is_edit': True, 'post': post, 'form': form}
    )


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', pk=post_id)


@login_required
def follow_index(request):
    posts = Post.objects.filter(author__following__user=request.user)
    page_obj = get_paginator_obj(posts, request)
    return render(request, 'posts/follow.html', {'page_obj': page_obj})


@login_required
def profile_follow(request, username):
    author = User.objects.get(username=username)
    if author != request.user:
        Follow.objects.get_or_create(
            user=request.user,
            author=author
        )
    return redirect('posts:profile', username)


@login_required
def profile_unfollow(request, username):
    # author = User.objects.get(username=username)
    is_follower = Follow.objects.filter(author__following__user=request.user)
    if is_follower:
        is_follower.delete()
    return redirect('posts:profile', username)
