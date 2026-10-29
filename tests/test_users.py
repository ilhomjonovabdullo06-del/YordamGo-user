"""
tests.test_users — users moduli uchun Django testlari.

Testlar:
    UserCreationTest        — User modeli va UserManager testlari
    ProfileAutoCreateTest   — Signal orqali profil avtomatik yaratilishini tekshirish
    AuthViewTest            — Ro'yxatdan o'tish, kirish, chiqish testlari
    APIEndpointTest         — DRF API endpointlari testlari
"""
from django.test import Client
from django.urls import reverse
from rest_framework.test import APIClient

from apps.users.models import User, WorkerProfile, EmployerProfile

from .base import YGTestCase as TestCase  # tez parol hasher'i bilan


class UserCreationTest(TestCase):
    """User modeli va UserManager testlari."""

    def test_create_worker_user(self):
        """Ishchi foydalanuvchini to'g'ri yaratish."""
        user = User.objects.create_user(
            phone_number="+998901111111",
            password="TestPass123!",
            first_name="Ali",
            last_name="Valiyev",
            role=User.Role.WORKER,
        )
        self.assertEqual(user.phone_number, "+998901111111")
        self.assertEqual(user.role, User.Role.WORKER)
        self.assertTrue(user.check_password("TestPass123!"))
        self.assertFalse(user.is_verified)
        self.assertFalse(user.is_staff)

    def test_create_employer_user(self):
        """Ish beruvchi foydalanuvchini to'g'ri yaratish."""
        user = User.objects.create_user(
            phone_number="+998902222222",
            password="TestPass123!",
            first_name="Bobur",
            last_name="Rahimov",
            role=User.Role.EMPLOYER,
        )
        self.assertEqual(user.role, User.Role.EMPLOYER)
        self.assertTrue(user.is_employer)
        self.assertFalse(user.is_worker)

    def test_create_superuser(self):
        """Superuserni to'g'ri yaratish."""
        admin = User.objects.create_superuser(
            phone_number="+998909999999",
            password="AdminPass123!",
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_user_str(self):
        """User __str__ metodi to'g'ri ishlashi."""
        user = User.objects.create_user(
            phone_number="+998903333333",
            password="TestPass123!",
            first_name="Zafar",
            last_name="Toshev",
        )
        self.assertIn("+998903333333", str(user))
        self.assertIn("Zafar", str(user))

    def test_phone_number_required(self):
        """Telefon raqamsiz foydalanuvchi yaratib bo'lmasligi."""
        with self.assertRaises(ValueError):
            User.objects.create_user(phone_number="", password="TestPass123!")


class ProfileAutoCreateTest(TestCase):
    """Signal orqali profil avtomatik yaratilishini tekshirish."""

    def test_worker_profile_auto_created(self):
        """Ishchi foydalanuvchi yaratilganda WorkerProfile avtomatik yaratilishi."""
        user = User.objects.create_user(
            phone_number="+998904444444",
            password="TestPass123!",
            first_name="Kamol",
            last_name="Mirzayev",
            role=User.Role.WORKER,
        )
        # Signal ishlagani uchun WorkerProfile bo'lishi kerak
        self.assertTrue(WorkerProfile.objects.filter(user=user).exists())
        self.assertFalse(EmployerProfile.objects.filter(user=user).exists())

    def test_employer_profile_auto_created(self):
        """Ish beruvchi yaratilganda EmployerProfile avtomatik yaratilishi."""
        user = User.objects.create_user(
            phone_number="+998905555555",
            password="TestPass123!",
            first_name="Sarvar",
            last_name="Xolmatov",
            role=User.Role.EMPLOYER,
        )
        self.assertTrue(EmployerProfile.objects.filter(user=user).exists())
        self.assertFalse(WorkerProfile.objects.filter(user=user).exists())

    def test_worker_profile_default_values(self):
        """WorkerProfile boshlang'ich qiymatlari to'g'ri ekanligi."""
        user = User.objects.create_user(
            phone_number="+998906666666",
            password="TestPass123!",
            role=User.Role.WORKER,
        )
        profile = user.worker_profile
        self.assertEqual(float(profile.rating), 0.0)
        self.assertEqual(profile.completed_jobs_count, 0)
        self.assertEqual(profile.bio, "")

    def test_employer_profile_default_values(self):
        """EmployerProfile boshlang'ich qiymatlari to'g'ri ekanligi."""
        user = User.objects.create_user(
            phone_number="+998907777777",
            password="TestPass123!",
            role=User.Role.EMPLOYER,
        )
        profile = user.employer_profile
        self.assertEqual(float(profile.rating), 0.0)
        self.assertEqual(profile.posted_jobs_count, 0)
        self.assertEqual(profile.company_name, "")

    def test_profile_str(self):
        """WorkerProfile va EmployerProfile __str__ metodlari."""
        worker = User.objects.create_user(
            phone_number="+998908888881",
            password="TestPass123!",
            first_name="Test",
            last_name="Worker",
            role=User.Role.WORKER,
        )
        employer = User.objects.create_user(
            phone_number="+998908888882",
            password="TestPass123!",
            first_name="Test",
            last_name="Employer",
            role=User.Role.EMPLOYER,
        )
        self.assertIn("Ishchi", str(worker.worker_profile))
        self.assertIn("Ish beruvchi", str(employer.employer_profile))


class AuthViewTest(TestCase):
    """Ro'yxatdan o'tish, kirish va chiqish view'lari testlari."""

    def setUp(self):
        """Test uchun dastlabki foydalanuvchi."""
        self.client = Client()
        self.existing_user = User.objects.create_user(
            phone_number="+998900000001",
            password="ExistingPass123!",
            first_name="Mavjud",
            last_name="Foydalanuvchi",
            role=User.Role.WORKER,
        )

    def test_register_page_loads(self):
        """Ro'yxatdan o'tish sahifasi yuklanganligi."""
        response = self.client.get(reverse("users:register"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/register.html")

    def test_register_new_worker(self):
        """Yangi ishchini ro'yxatdan o'tkazish."""
        data = {
            "phone_number": "+998910000001",
            "first_name": "Yangi",
            "last_name": "Ishchi",
            "role": "worker",
            "password1": "NewPass123!",
            "password2": "NewPass123!",
        }
        response = self.client.post(reverse("users:register"), data)
        self.assertEqual(response.status_code, 302)  # Muvaffaqiyatli redirect
        self.assertTrue(User.objects.filter(phone_number="+998910000001").exists())

    def test_register_new_employer(self):
        """Yangi ish beruvchini ro'yxatdan o'tkazish."""
        data = {
            "phone_number": "+998910000002",
            "first_name": "Yangi",
            "last_name": "Ish Beruvchi",
            "role": "employer",
            "password1": "NewPass123!",
            "password2": "NewPass123!",
        }
        response = self.client.post(reverse("users:register"), data)
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(phone_number="+998910000002")
        self.assertTrue(EmployerProfile.objects.filter(user=user).exists())

    def test_register_duplicate_phone(self):
        """Mavjud telefon raqam bilan ro'yxatdan o'tib bo'lmasligi."""
        data = {
            "phone_number": "+998900000001",  # allaqachon mavjud
            "first_name": "Duplikat",
            "last_name": "Foydalanuvchi",
            "role": "worker",
            "password1": "NewPass123!",
            "password2": "NewPass123!",
        }
        response = self.client.post(reverse("users:register"), data)
        self.assertEqual(response.status_code, 200)  # Xato bilan qaytadi
        form = response.context["form"]
        self.assertFormError(
            form, "phone_number",
            "Bu telefon raqam allaqachon ro'yxatdan o'tgan."
        )

    def test_login_page_loads(self):
        """Kirish sahifasi yuklanganligi."""
        response = self.client.get(reverse("users:login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/login.html")

    def test_login_with_correct_credentials(self):
        """To'g'ri ma'lumotlar bilan kirish."""
        data = {
            "phone_number": "+998900000001",
            "password": "ExistingPass123!",
        }
        response = self.client.post(reverse("users:login"), data)
        self.assertEqual(response.status_code, 302)

    def test_login_with_wrong_password(self):
        """Noto'g'ri parol bilan kirish imkonsizligi."""
        data = {
            "phone_number": "+998900000001",
            "password": "WrongPassword!",
        }
        response = self.client.post(reverse("users:login"), data)
        self.assertEqual(response.status_code, 200)  # Xato bilan qaytadi

    def test_logout(self):
        """Tizimdan chiqish."""
        self.client.login(phone_number="+998900000001", password="ExistingPass123!")
        response = self.client.post(reverse("users:logout"))
        self.assertEqual(response.status_code, 302)

    def test_profile_requires_login(self):
        """Tizimga kirmasdan profil sahifasiga kira olmaslik."""
        response = self.client.get(reverse("users:profile"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/users/login/", response.url)


class APIEndpointTest(TestCase):
    """DRF API endpointlari testlari."""

    def setUp(self):
        """Test uchun API client va foydalanuvchi."""
        self.api_client = APIClient()
        self.user = User.objects.create_user(
            phone_number="+998920000001",
            password="APITestPass123!",
            first_name="API",
            last_name="Tester",
            role=User.Role.WORKER,
        )

    def test_api_register_worker(self):
        """API orqali yangi ishchini ro'yxatdan o'tkazish."""
        data = {
            "phone_number": "+998920000002",
            "first_name": "API",
            "last_name": "Worker",
            "role": "worker",
            "password": "APIPass123!",
            "password2": "APIPass123!",
        }
        response = self.api_client.post("/api/users/register/", data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["phone_number"], "+998920000002")

    def test_api_profile_requires_auth(self):
        """Autentifikatsiyasiz API profilga kira olmaslik."""
        response = self.api_client.get("/api/users/profile/")
        self.assertEqual(response.status_code, 403)

    def test_api_profile_authenticated(self):
        """Autentifikatsiya bilan API profil olish."""
        self.api_client.force_authenticate(user=self.user)
        response = self.api_client.get("/api/users/profile/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["phone_number"], "+998920000001")
