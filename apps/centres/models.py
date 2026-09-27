import uuid
from django.db import models


class DiagnosticCentre(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)
    location = models.CharField(max_length=255, help_text="City or primary location area", db_index=True)
    address = models.TextField()
    city = models.CharField(max_length=100, db_index=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Diagnostic Centre'
        verbose_name_plural = 'Diagnostic Centres'

    def __str__(self):
        return f"{self.name} - {self.location}"


class DiagnosticTest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    category = models.CharField(max_length=100, default='General', db_index=True)
    description = models.TextField(blank=True)
    preparation_instructions = models.TextField(blank=True, help_text="e.g., 10-hour fasting required")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Diagnostic Test'
        verbose_name_plural = 'Diagnostic Tests'

    def __str__(self):
        return f"{self.name} ({self.code})"


class CentreTest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    centre = models.ForeignKey(DiagnosticCentre, on_delete=models.CASCADE, related_name='offered_tests')
    test = models.ForeignKey(DiagnosticTest, on_delete=models.CASCADE, related_name='offering_centres')
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Test price at this specific centre")
    is_available = models.BooleanField(default=True)
    estimated_hours = models.PositiveIntegerField(default=24, help_text="Report turnaround time in hours")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['centre', 'test']
        unique_together = ('centre', 'test')
        verbose_name = 'Centre Test Pricing'
        verbose_name_plural = 'Centre Test Pricings'

    def __str__(self):
        return f"{self.test.name} at {self.centre.name} - ₹{self.price}"
