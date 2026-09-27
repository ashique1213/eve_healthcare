from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from apps.centres.models import DiagnosticCentre, DiagnosticTest, CentreTest
from apps.bookings.models import Booking

User = get_user_model()


class Command(BaseCommand):
    help = 'Seeds initial diagnostic centres, tests, pricing, and admin/patient user accounts.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Seeding database with initial data...'))

        # 1. Create Admin User
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@evehealthcare.com',
                'first_name': 'Admin',
                'last_name': 'System',
                'role': User.Role.ADMIN,
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            admin_user.set_password('Admin@123456')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('Created admin user: admin / Admin@123456'))

        # 2. Create Sample Patient User
        patient_user, created = User.objects.get_or_create(
            username='john_doe',
            defaults={
                'email': 'john@example.com',
                'first_name': 'John',
                'last_name': 'Doe',
                'role': User.Role.PATIENT,
                'phone_number': '+19876543210'
            }
        )
        if created:
            patient_user.set_password('Patient@123456')
            patient_user.save()
            self.stdout.write(self.style.SUCCESS('Created patient user: john_doe / Patient@123456'))

        # 3. Create Diagnostic Centres
        centre1, _ = DiagnosticCentre.objects.get_or_create(
            name='Apollo Diagnostics - Indiranagar',
            defaults={
                'location': 'Indiranagar',
                'city': 'Bangalore',
                'address': '100 Feet Rd, HAL 2nd Stage, Indiranagar, Bengaluru, Karnataka 560038',
                'contact_phone': '+918045678901',
                'contact_email': 'indiranagar@apollodiagnostics.com'
            }
        )

        centre2, _ = DiagnosticCentre.objects.get_or_create(
            name='Metropolis Healthcare - Koramangala',
            defaults={
                'location': 'Koramangala',
                'city': 'Bangalore',
                'address': '80 Feet Rd, 4th Block, Koramangala, Bengaluru, Karnataka 560034',
                'contact_phone': '+918045678902',
                'contact_email': 'koramangala@metropolis.in'
            }
        )

        centre3, _ = DiagnosticCentre.objects.get_or_create(
            name='Dr. Lal PathLabs - Connaught Place',
            defaults={
                'location': 'Connaught Place',
                'city': 'New Delhi',
                'address': 'Block E, Connaught Place, New Delhi 110001',
                'contact_phone': '+911145678903',
                'contact_email': 'cp@lalpathlabs.com'
            }
        )

        # 4. Create Diagnostic Tests
        test1, _ = DiagnosticTest.objects.get_or_create(
            code='TEST-CBC-01',
            defaults={
                'name': 'Complete Blood Count (CBC)',
                'category': 'Hematology',
                'description': 'Measures RBC, WBC, platelets, hemoglobin, and hematocrit levels.',
                'preparation_instructions': 'No special fasting required.'
            }
        )

        test2, _ = DiagnosticTest.objects.get_or_create(
            code='TEST-LFT-02',
            defaults={
                'name': 'Liver Function Test (LFT)',
                'category': 'Biochemistry',
                'description': 'Evaluates liver enzymes, bilirubin, albumin, and total proteins.',
                'preparation_instructions': 'Fasting for 8-10 hours recommended.'
            }
        )

        test3, _ = DiagnosticTest.objects.get_or_create(
            code='TEST-KFT-03',
            defaults={
                'name': 'Kidney Function Test (KFT / Renal Panel)',
                'category': 'Biochemistry',
                'description': 'Assesses creatinine, blood urea nitrogen (BUN), and electrolytes.',
                'preparation_instructions': 'Drink adequate water before sample collection.'
            }
        )

        test4, _ = DiagnosticTest.objects.get_or_create(
            code='TEST-THY-04',
            defaults={
                'name': 'Thyroid Profile (Total T3, T4, TSH)',
                'category': 'Endocrinology',
                'description': 'Measures thyroid hormones to screen for hyper/hypothyroidism.',
                'preparation_instructions': 'Fasting for 8 hours.'
            }
        )

        test5, _ = DiagnosticTest.objects.get_or_create(
            code='TEST-COVID-05',
            defaults={
                'name': 'RT-PCR COVID-19 Test',
                'category': 'Molecular Diagnostics',
                'description': 'Qualitative detection of SARS-CoV-2 viral RNA.',
                'preparation_instructions': 'Nasal swab collection.'
            }
        )

        # 5. Link Tests to Centres with Prices
        pricings = [
            (centre1, test1, 450.00, 12),
            (centre1, test2, 850.00, 24),
            (centre1, test4, 650.00, 24),
            (centre2, test1, 400.00, 12),
            (centre2, test3, 900.00, 24),
            (centre2, test5, 500.00, 8),
            (centre3, test2, 800.00, 24),
            (centre3, test3, 850.00, 24),
            (centre3, test4, 600.00, 24),
        ]

        for centre, test, price, est_hrs in pricings:
            ct, _ = CentreTest.objects.get_or_create(
                centre=centre,
                test=test,
                defaults={
                    'price': price,
                    'estimated_hours': est_hrs,
                    'is_available': True
                }
            )

        # 6. Create sample seed booking
        ct_apollo_cbc = CentreTest.objects.get(centre=centre1, test=test1)
        booking, bk_created = Booking.objects.get_or_create(
            user=patient_user,
            centre_test=ct_apollo_cbc,
            defaults={
                'appointment_datetime': timezone.now() + timedelta(days=2),
                'amount': ct_apollo_cbc.price,
                'status': Booking.Status.PENDING,
                'notes': 'Please send technician for home sample collection.'
            }
        )

        self.stdout.write(self.style.SUCCESS(f'Database successfully seeded! Sample Booking Ref: {booking.booking_reference}'))
