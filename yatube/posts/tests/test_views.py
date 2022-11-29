from http import HTTPStatus

from django import forms
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Post, Group, User, Follow, Comment

NUMBER_OF_POSTS: int = 1
NEW_POSTS: int = 13
POSTS_ON_FIRST_PAGE: int = 10
POSTS_ON_SECOND_PAGE: int = 3
FIRST_PAGE: int = 1
SECOND_PAGE: int = 2
ZERO: int = 0


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='HasNoName')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test_slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            text='Test post',
            author=cls.user,
            group=cls.group
        )
        cls.index = reverse('posts:index')
        cls.group_path = reverse(
            'posts:group_list', kwargs={'slug': 'test_slug'}
        )
        cls.profile = reverse(
            'posts:profile', kwargs={'username': 'HasNoName'}
        )
        cls.detail = reverse(
            'posts:post_detail', kwargs={'pk': NUMBER_OF_POSTS}
        )
        cls.create = reverse('posts:post_create')
        cls.edit = reverse(
            'posts:post_edit', kwargs={'post_id': NUMBER_OF_POSTS}
        )

        cls.templates_pages_name = {
            cls.index: 'posts/index.html',
            cls.group_path: 'posts/group_list.html',
            cls.profile: 'posts/profile.html',
            cls.detail: 'posts/post_detail.html'
        }
        cls.templates_pages_name_2 = {
            cls.create: 'posts/create_post.html',
            cls.edit: 'posts/create_post.html'
        }

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_index_cache(self):
        """Проверка кеша главной страницы"""
        response = self.authorized_client.get(self.index)
        content_before_del_post = response.content
        Post.objects.all().delete()
        response_after_del_post = self.authorized_client.get(
            self.index
        )
        content_after_del_post = response_after_del_post.content
        self.assertEqual(content_before_del_post, content_after_del_post)
        # Очищаем кеш и проверяем на изменение ответа
        cache.clear()
        response_after_clear_cache = self.authorized_client.get(
            self.index
        )
        content_after_clear_cache = response_after_clear_cache.content
        self.assertNotEqual(content_after_del_post, content_after_clear_cache)

    def test_pages_uses_correct_template(self):
        """URL адрес использует свой шаблон"""
        url_template = {
            **self.templates_pages_name,
            **self.templates_pages_name_2
        }
        for reverse_name, template in url_template.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_correct_context(self):
        """Проверка контекста на страницах сайта"""
        for address in self.templates_pages_name:
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertEqual(
                    response.context['post'].text,
                    self.post.text
                )
                self.assertEqual(
                    response.context['post'].author,
                    self.user
                )
                self.assertEqual(
                    response.context['post'].group,
                    self.group
                )
                self.assertEqual(
                    response.context['post'].id,
                    NUMBER_OF_POSTS
                )

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом"""
        response = self.authorized_client.get(self.index)
        self.assertEqual(
            len(response.context['page_obj']),
            NUMBER_OF_POSTS
        )

    def test_post_create_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом"""
        response = self.authorized_client.get(self.create)
        form_fields = {
            'text': forms.CharField,
            'group': forms.ChoiceField}
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_post_edit_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом"""
        form_data = {'text': 'redact text', 'group': self.group.id}
        self.authorized_client.post(reverse(
            'posts:post_edit',
            kwargs={'post_id': self.post.id}),
            data=form_data, follow=True)
        edit_post = Post.objects.get(id=self.post.id)
        self.assertEqual(edit_post.text, form_data['text'])

    def test_post_added_correctly(self):
        """Пост при создании добавлен корректно"""
        for address in self.templates_pages_name:
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertEqual(
                    response.context['post'].text,
                    self.post.text
                )

    def test_comment_post_is_forbidden_for_guest_client(self):
        """Не авторизованный пользователь
         не может комментировать пост"""
        comment = Comment.objects.count()
        self.guest_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': self.post.id}
            ),
            data={'text': 'Test comment'},
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comment)

    def test_comment_post_for_authorized_client(self):
        """Комментарий после успешной отправки
         появляется на странице поста"""
        self.authorized_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': self.post.id}
            ),
            data={'text': 'Test comment'},
            follow=True
        )
        self.assertEqual(Comment.objects.count(), NUMBER_OF_POSTS)


class PaginatorViewsTest(TestCase):

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='HasNoName')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug'
        )
        post_list = []
        for i in range(NEW_POSTS):
            post_list.append(Post(
                text=f'Тестовый текст {i}',
                group=self.group,
                author=self.user)
            )
        Post.objects.bulk_create(post_list)

    def test_correct_records_contains_on_page(self):
        """Проверка количества постов на первой и второй странице"""
        postfixurl_posts = [
            (FIRST_PAGE, POSTS_ON_FIRST_PAGE),
            (SECOND_PAGE, POSTS_ON_SECOND_PAGE)
        ]
        templates_pages_name = [
            reverse('posts:index'),
            reverse(
                'posts:group_list',
                kwargs={'slug': 'test-slug'}
            ),
            reverse(
                'posts:profile',
                kwargs={'username': 'HasNoName'}
            )
        ]

        for postfixurl, posts in postfixurl_posts:
            for page in templates_pages_name:
                with self.subTest(page=page):
                    response = self.authorized_client.get(
                        page, {'page': postfixurl}
                    )
                    self.assertEqual(len(
                        response.context['page_obj']), posts
                    )


class ViewFollowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.follower_user = User.objects.create_user(username='user')
        cls.user = User.objects.create_user(username='user2')
        cls.following_user = User.objects.create_user(username='user3')
        cls.follow_count = Follow.objects.count()

    def setUp(self):
        self.guest_client = Client()
        self.follower_client = Client()
        self.follower_client.force_login(self.follower_user)
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.following_client = Client()
        self.following_client.force_login(self.following_user)
        cache.clear()

    def test_authorized_client_can_subscribe(self):
        """Авторизованный пользователь может подписаться"""
        response = self.follower_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.following_user}
            )
        )
        self.assertRedirects(
            response, reverse(
                'posts:profile', kwargs={'username': self.following_user}
            )
        )
        self.assertEqual(
            Follow.objects.count(),
            self.follow_count + NUMBER_OF_POSTS
        )
        self.assertTrue(
            Follow.objects.filter(
                user=self.follower_user,
                author=self.following_user
            ).exists()
        )

    def test_authorized_client_can_unsubscribe(self):
        """Авторизованный пользователь может отписаться"""
        response = self.follower_client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.following_user}
            )
        )
        self.assertEqual(Follow.objects.count(), self.follow_count)
        self.assertRedirects(
            response, reverse(
                'posts:profile', kwargs={'username': self.following_user}
            )
        )

    def test_following_post_in_follower_index_context(self):
        """Новая запись пользователя появляется в ленте подписчика и
        не появляется в ленте других"""
        post = Post.objects.create(
            text='Test post',
            author=self.following_user
        )
        Follow.objects.create(
            user=self.follower_user,
            author=self.following_user
        )
        response_follower = self.follower_client.get(
            reverse(
                'posts:follow_index'
            )
        )
        response_authorized_client = self.authorized_client.get(
            reverse(
                'posts:follow_index'
            )
        )
        self.assertEqual(response_follower.context['post'].text, post.text)
        self.assertEqual(
            response_follower.context['post'].author,
            post.author
        )
        self.assertEqual(response_follower.context['post'].group, None)
        self.assertNotIn(post, response_authorized_client.context['page_obj'])

    def test_guest_client_cant_subscribe(self):
        """Неавторизованный клиент не может подписаться"""
        response = self.guest_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.following_client}
            )
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(Follow.objects.count(), ZERO)
