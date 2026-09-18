from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .models import User, nz_phone


class PhoneFormatTests(SimpleTestCase):
    def test_documented_phone_formats_are_accepted(self):
        for number in ['021 123 4567', '0211234567', '+64 21 123 4567',
                       '09 555 1234', '095551234', '09 555 0177']:
            with self.subTest(number=number):
                nz_phone(number)

    def test_invalid_phone_formats_are_rejected(self):
        for number in ['abc', '123', '021 555 words', '+61 21 123 4567',
                       '02112345678901234']:
            with self.subTest(number=number):
                with self.assertRaises(ValidationError):
                    nz_phone(number)


class LoginEmailTests(TestCase):
    def test_sign_in_accepts_case_variations_of_a_registered_email(self):
        user = User.objects.create_user(
            email='himani@example.com', password='a-long-enough-test-password',
            first_name='Test', last_name='User', phone='021 555 0000')
        response = self.client.post(reverse('accounts:login'), {
            'username': 'Himani@EXAMPLE.COM',
            'password': 'a-long-enough-test-password',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)
