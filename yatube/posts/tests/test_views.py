from django import forms
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Post, Group, User, Follow

NUMBER_OF_POSTS: int = 1
NEW_POSTS: int = 13
POSTS_ON_FIRST_PAGE: int = 10
POSTS_ON_SECOND_PAGE: int = 3
FIRST_PAGE: int = 1
SECOND_PAGE: int = 2


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
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_index_cache(self):
        """Проверка кеша главной страницы"""
        response = self.authorized_client.get(reverse('posts:index'))
        content1 = response.content
        Post.objects.all().delete()
        response2 = self.authorized_client.get(reverse('posts:index'))
        content2 = response2.content
        self.assertEqual(content1, content2)
        """Очищаем кеш и проверяем на изменение ответа"""
        cache.clear()
        response3 = self.authorized_client.get(reverse('posts:index'))
        content3 = response3.content
        self.assertNotEqual(content2, content3)

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
        cls.user = User.objects.create_user(username='user')
        cls.user2 = User.objects.create_user(username='user2')
        cls.user3 = User.objects.create_user(username='user3')

    def setUp(self):
        self.authorized_client1 = Client()
        self.authorized_client1.force_login(self.user)
        self.authorized_client2 = Client()
        self.authorized_client2.force_login(self.user2)
        self.following_client = Client()
        self.following_client.force_login(self.user3)
        cache.clear()

    def test_authorized_client_can_subscribe_un(self):
        """Авторизованный пользователь может подписаться и отписаться"""
        follow_count = Follow.objects.count()
        response = self.authorized_client1.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.user3}
            )
        )
        self.assertRedirects(
            response, reverse(
                'posts:profile', kwargs={'username': self.user3}
            )
        )
        self.assertEqual(Follow.objects.count(), follow_count + NUMBER_OF_POSTS)
        self.assertTrue(
            Follow.objects.filter(
                user=self.user,
                author=self.user3
            ).exists()
        )
        response2 = self.authorized_client1.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.user3}
            )
        )
        self.assertEqual(Follow.objects.count(), follow_count)
        self.assertRedirects(
            response2, reverse(
                'posts:profile', kwargs={'username': self.user3}
            )
        )

    def test_following_post_in_follower_index_context(self):
        """Новая запись пользователя появляется в ленте подписчика и
        не появляется в ленте других"""
        post = Post.objects.create(
            text='Test post',
            author=self.user3
        )
        Follow.objects.create(
            user=self.user,
            author=self.user3
        )
        response = self.authorized_client1.get(
            reverse(
                'posts:follow_index'
            )
        )
        response2 = self.authorized_client2.get(
            reverse(
                'posts:follow_index'
            )
        )
        self.assertEqual(response.context['post'].text, post.text)
        self.assertEqual(response.context['post'].author, post.author)
        self.assertEqual(response.context['post'].group, None)
        self.assertNotIn(post, response2.context['page_obj'])
