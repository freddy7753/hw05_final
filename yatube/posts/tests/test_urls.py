from http import HTTPStatus

from django.core.cache import cache
from django.test import Client, TestCase

from ..models import Group, Post, User


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='HasNoName')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user
        )
        cls.templates_url_names_public = {
            '/': 'posts/index.html',
            f'/group/{cls.group.slug}/': 'posts/group_list.html',
            f'/profile/{cls.user}/': 'posts/profile.html',
            f'/posts/{cls.post.id}/': 'posts/post_detail.html',
        }
        cls.templates_url_names_privet = {
            '/create/': 'posts/create_post.html',
            f'/posts/{cls.post.id}/edit/': 'posts/create_post.html',
            '/follow/': 'posts/follow.html'
        }

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_posts_urls_exists_at_desired_location(self):
        """Проверяем адреса на доступность авторизованным клиентом"""
        path = {
            **self.templates_url_names_public,
            **self.templates_url_names_privet
        }
        for address in path:
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_posts_urls_exists_for_guest_client(self):
        """Проверяем доступность адресов для
         неавторизованного клиента"""
        for address in self.templates_url_names_public:
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(
                    response.status_code,
                    HTTPStatus.OK
                )

    def test_post_create_edit_for_guest_client(self):
        """Проверяем страницу создания и
         редактирования поста на redirect"""
        for address in self.templates_url_names_privet:
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(
                    response.status_code,
                    HTTPStatus.FOUND
                )

    def test_for_unexpected_page(self):
        """Проверяем на несуществующую страницу"""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateUsed(response, 'core/404.html')

    def test_urls_uses_correct_template(self):
        """Url-адрес использует соответсвующий шаблон"""
        urls_template = {
            **self.templates_url_names_public,
            **self.templates_url_names_privet
        }
        for address, template in urls_template.items():
            # Для авторизованного пользователя
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)
