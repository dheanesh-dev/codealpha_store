from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Profile

GOOD_PASSWORD = 'Sup3r-Secret!42'


class AuthTests(TestCase):
    def register(self, **overrides):
        data = {'first_name': 'Asha', 'username': 'asha', 'email': 'asha@example.com',
                'password1': GOOD_PASSWORD, 'password2': GOOD_PASSWORD}
        data.update(overrides)
        return self.client.post(reverse('accounts:register'), data)

    def test_register_creates_user_profile_and_logs_in(self):
        response = self.register()
        self.assertRedirects(response, reverse('store:home'))
        user = User.objects.get(username='asha')
        self.assertTrue(Profile.objects.filter(user=user).exists())
        self.assertNotEqual(user.password, GOOD_PASSWORD)  # hashed
        self.assertIn('_auth_user_id', self.client.session)

    def test_weak_password_rejected(self):
        response = self.register(password1='12345678', password2='12345678')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='asha').exists())
        self.assertContains(response, 'too common')

    def test_duplicate_email_rejected(self):
        self.register()
        self.client.logout()
        response = self.register(username='other')
        self.assertContains(response, 'already exists')
        self.assertEqual(User.objects.count(), 1)

    def test_login_and_logout(self):
        User.objects.create_user('bob', 'bob@example.com', GOOD_PASSWORD)
        response = self.client.post(reverse('accounts:login'), {'username': 'bob', 'password': GOOD_PASSWORD})
        self.assertRedirects(response, reverse('store:home'))
        self.client.post(reverse('accounts:logout'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_wrong_password_shows_error(self):
        User.objects.create_user('bob', 'bob@example.com', GOOD_PASSWORD)
        response = self.client.post(reverse('accounts:login'), {'username': 'bob', 'password': 'nope'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please enter a correct')

    def test_profile_requires_login(self):
        response = self.client.get(reverse('accounts:profile'))
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={reverse('accounts:profile')}")

    def test_profile_view_and_edit(self):
        User.objects.create_user('bob', 'bob@example.com', GOOD_PASSWORD)
        self.client.login(username='bob', password=GOOD_PASSWORD)
        self.assertEqual(self.client.get(reverse('accounts:profile')).status_code, 200)
        response = self.client.post(reverse('accounts:profile_edit'), {
            'first_name': 'Bob', 'last_name': 'Ray', 'email': 'bob2@example.com',
            'phone': '9876543210', 'city': 'Chennai'})
        self.assertRedirects(response, reverse('accounts:profile'))
        user = User.objects.get(username='bob')
        self.assertEqual(user.email, 'bob2@example.com')
        self.assertEqual(user.profile.city, 'Chennai')

    def test_profile_edit_rejects_bad_phone(self):
        User.objects.create_user('bob', 'bob@example.com', GOOD_PASSWORD)
        self.client.login(username='bob', password=GOOD_PASSWORD)
        response = self.client.post(reverse('accounts:profile_edit'), {
            'first_name': 'Bob', 'email': 'bob@example.com', 'phone': 'abc', 'city': ''})
        self.assertContains(response, 'valid phone number')
