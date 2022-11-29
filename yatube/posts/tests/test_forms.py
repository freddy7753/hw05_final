import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from ..forms import PostForm
from ..models import Group, Post, User

ONE_POST: int = 1
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
SMALL_GIF = (
    b'\x47\x49\x46\x38\x39\x61\x02\x00'
    b'\x01\x00\x80\x00\x00\x00\x00\x00'
    b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
    b'\x00\x00\x00\x2C\x00\x00\x00\x00'
    b'\x02\x00\x01\x00\x00\x02\x02\x0C'
    b'\x0A\x00\x3B'
)
UPLOADED = SimpleUploadedFile(
    name='small.gif',
    content=SMALL_GIF,
    content_type='image/gif'
)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='user')
        cls.form = PostForm()
        cls.posts_count = Post.objects.count()
        cls.group = Group.objects.create(
            title='Test title',
            slug='test_slug',
            description='Test description'
        )
        cls.form_data = {
            'text': 'Test post',
            'group': cls.group
        }

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """Проверка на создание нового поста"""
        self.authorized_client.post(
            reverse('posts:post_create'),
            data=self.form_data,
            follow=True
        )
        post_id = Post.objects.order_by('-pub_date')[0].id
        response = self.authorized_client.get(reverse(
            'posts:post_detail',
            kwargs={'pk': post_id}
        ))
        self.assertEqual(
            Post.objects.count(),
            self.posts_count + ONE_POST
        )
        self.assertEqual(
            response.context['post'].text,
            self.form_data['text']
        )
        self.assertEqual(response.context['post'].group, None)
        self.assertEqual(response.context['post'].author, self.user)

    def test_create_post_is_forbidden_for_guest_client(self):
        """Незарегистрированный пользователь не может создать пост"""
        self.guest_client.post(
            reverse('posts:post_create'),
            data=self.form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), self.posts_count)

    def test_for_redact_post(self):
        """Тест на редактирование поста"""
        post = Post.objects.create(
            text='Test post',
            group=self.group,
            author=self.user
        )
        self.authorized_client.post(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': post.id}
            ),
            data=self.form_data,
            follow=True
        )
        post_id = Post.objects.first().id
        post = Post.objects.get(pk=post_id)
        self.assertEqual(post.text, self.form_data['text'])
        self.assertEqual(post.group, self.group)
        self.assertEqual(post.author, self.user)

    def test_create_post(self):
        """Валидная форма создает запись с картинкой в Post."""
        form_data = {
            'text': 'Тестовый пост',
            'group': self.group.id,
            'image': UPLOADED
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse(
                'posts:profile',
                kwargs={'username': self.user}
            )
        )
        self.assertEqual(
            Post.objects.count(),
            self.posts_count + ONE_POST)
        self.assertTrue(
            Post.objects.filter(text=form_data['text']).exists()
        )
        first_object = Post.objects.last()
        self.assertEqual(first_object.image, 'posts/small.gif')
        self.assertEqual(first_object.text, form_data['text'])
        self.assertEqual(first_object.group, self.group)

    def test_image_post(self):
        """При выводе поста с картинкой изображение есть в словаре"""
        post = Post.objects.create(
            author=self.user,
            text='Test post',
            group=self.group,
            image=UPLOADED
        )
        list_pages_names = (
            reverse('posts:index'),
            reverse('posts:post_detail',
                    kwargs={'pk': post.id}),
            reverse('posts:profile', kwargs={'username': self.user}),
            reverse('posts:group_list', kwargs={'slug': 'test_slug'}),
        )
        for page in list_pages_names:
            with self.subTest(page=page):
                response = self.authorized_client.get(page)
                self.assertEqual(response.context['post'].image, post.image)
                self.assertEqual(response.context['post'].text, post.text)
                self.assertEqual(response.context['post'].group, post.group)
                self.assertEqual(response.context['post'].author, self.user)
