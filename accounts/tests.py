"""Authentication tests: registration, the sign-in throttle, and role escalation."""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

User = get_user_model()

GOOD_PASSWORD = 'correct-horse-battery'


class SignUpTests(TestCase):
    def form(self, **overrides):
        data = {
            'first_name': 'Himani', 'last_name': 'Thapa Magar',
            'email': 'Himani@Example.com', 'phone': '021 555 0110', 'suburb': 'Mt Eden',
            'password1': GOOD_PASSWORD, 'password2': GOOD_PASSWORD,
        }
        data.update(overrides)
        return data

    def test_sign_up_creates_a_customer(self):
        self.client.post(reverse('accounts:signup'), self.form())
        user = User.objects.get(email='himani@example.com')
        self.assertEqual(user.role_names, ['Customer'])

    def test_email_is_stored_lower_case(self):
        # Otherwise Himani@example.com and himani@example.com become two accounts and the
        # unique constraint quietly does nothing useful.
        self.client.post(reverse('accounts:signup'), self.form())
        self.assertTrue(User.objects.filter(email='himani@example.com').exists())

    def test_a_visitor_cannot_give_themselves_a_staff_role(self):
        # The form has no role field, so this posts one anyway. If it ever worked, the whole
        # permission model would be decoration.
        self.client.post(reverse('accounts:signup'),
                         self.form(role='Administrator', is_staff='on', is_superuser='on'))
        user = User.objects.get(email='himani@example.com')
        self.assertEqual(user.role_names, ['Customer'])
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_a_short_password_is_rejected(self):
        response = self.client.post(reverse('accounts:signup'),
                                    self.form(password1='short1234', password2='short1234'))
        self.assertFalse(User.objects.filter(email='himani@example.com').exists())
        self.assertContains(response, 'at least 12 characters')

    def test_a_common_password_is_rejected(self):
        response = self.client.post(reverse('accounts:signup'),
                                    self.form(password1='password1234', password2='password1234'))
        self.assertFalse(User.objects.filter(email='himani@example.com').exists())
        self.assertEqual(response.status_code, 200)

    def test_a_duplicate_email_is_rejected(self):
        User.objects.create_user(email='himani@example.com', password=GOOD_PASSWORD,
                                 first_name='A', last_name='B', phone='021 555 0000')
        self.client.post(reverse('accounts:signup'), self.form())
        self.assertEqual(User.objects.filter(email='himani@example.com').count(), 1)


class LoginThrottleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='someone@example.com', password=GOOD_PASSWORD,
            first_name='Some', last_name='One', phone='021 555 0000')

    def setUp(self):
        cache.clear()

    def attempt(self, password):
        return self.client.post(reverse('accounts:login'),
                                {'username': 'someone@example.com', 'password': password})

    def test_the_account_locks_after_five_failures(self):
        for _ in range(5):
            self.attempt('wrong-password-here')
        response = self.attempt(GOOD_PASSWORD)   # the right password, but too late
        self.assertContains(response, 'Try again in 15 minutes')
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_a_successful_sign_in_clears_the_counter(self):
        for _ in range(3):
            self.attempt('wrong-password-here')
        self.attempt(GOOD_PASSWORD)
        self.assertEqual(cache.get('login-fail:someone@example.com'), None)

    def test_the_failure_message_does_not_confirm_the_account_exists(self):
        known = self.attempt('wrong-password-here')
        unknown = self.client.post(reverse('accounts:login'),
                                   {'username': 'nobody@example.com',
                                    'password': 'wrong-password-here'})
        message = 'do not match an account'
        self.assertContains(known, message)
        self.assertContains(unknown, message)


class ProfileTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='someone@example.com', password=GOOD_PASSWORD,
            first_name='Some', last_name='One', phone='021 555 0000')

    def test_a_signed_in_user_can_correct_their_own_details(self):
        self.client.force_login(self.user)
        self.client.post(reverse('accounts:profile'), {
            'first_name': 'Some', 'last_name': 'Onealtered',
            'phone': '021 555 0999', 'suburb': 'Grey Lynn'})
        self.user.refresh_from_db()
        self.assertEqual(self.user.suburb, 'Grey Lynn')

    def test_the_profile_form_cannot_change_the_email_address(self):
        # Email is the sign-in identifier, so it is not on the form. Posting it changes nothing.
        self.client.force_login(self.user)
        self.client.post(reverse('accounts:profile'), {
            'first_name': 'Some', 'last_name': 'One', 'phone': '021 555 0000',
            'suburb': '', 'email': 'attacker@example.com'})
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'someone@example.com')

    def test_the_profile_page_needs_a_sign_in(self):
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)
