from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


# ==================== USER & PROFILE ====================
class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('staff', 'Staff'),
        ('admin', 'Admin'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=200, blank=True, verbose_name="Full Name")
    phone_number = models.CharField(max_length=20, blank=True, verbose_name="Phone Number")
    address = models.TextField(blank=True, verbose_name="Address")
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name="Avatar")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user', verbose_name="Role")
    is_email_verified = models.BooleanField(default=False, verbose_name="Email Verified")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile {self.user.username}"

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"


# ==================== ROOM & AMENITIES ====================
class AmenityType(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Amenity Name")
    icon = models.CharField(max_length=50, blank=True, verbose_name="Icon/Emoji")
    description = models.TextField(blank=True, verbose_name="Description")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Amenity Type"
        verbose_name_plural = "Amenity Types"


class Room(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('maintenance', 'Maintenance'),
        ('inactive', 'Inactive'),
    ]

    name = models.CharField(max_length=100, verbose_name="Room Name")
    location = models.CharField(max_length=100, verbose_name="Location")
    capacity = models.PositiveIntegerField(verbose_name="Capacity")
    description = models.TextField(blank=True, verbose_name="Description")
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)], verbose_name="Price per Hour")
    is_available = models.BooleanField(default=True, verbose_name="Available")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="Status")
    amenities = models.ManyToManyField(AmenityType, blank=True, verbose_name="Amenities")
    image = models.ImageField(upload_to='rooms/', blank=True, null=True, verbose_name="Room Image")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.location})"

    class Meta:
        verbose_name = "Room"
        verbose_name_plural = "Rooms"




class BlackoutDate(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='blackout_dates', verbose_name="Room")
    date = models.DateField(verbose_name="Date")
    reason = models.CharField(max_length=200, blank=True, verbose_name="Reason")
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        if BlackoutDate.objects.filter(room=self.room, date=self.date).exclude(pk=self.pk).exists():
            raise ValidationError('A blackout date for this room already exists on this date.')

    class Meta:
        verbose_name = "Blackout Date"
        verbose_name_plural = "Blackout Dates"
        unique_together = ['room', 'date']


# ==================== BOOKING & PAYMENTS ====================
class Booking(models.Model):
    def clean(self):
        from django.core.exceptions import ValidationError
        overlapping = Booking.objects.filter(
            room=self.room,
            booking_date=self.booking_date,
        ).exclude(pk=self.pk).filter(
            start_time__lt=self.end_time,
            end_time__gt=self.start_time,
        )
        if overlapping.exists():
            raise ValidationError('This booking overlaps with an existing booking for the same room.')
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    booking_code = models.CharField(max_length=20, unique=True, default='TEMP', verbose_name="Booking Code")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings', verbose_name="User")
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='bookings', verbose_name="Room")
    booking_date = models.DateField(verbose_name="Booking Date")
    start_time = models.TimeField(verbose_name="Start Time")
    end_time = models.TimeField(verbose_name="End Time")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Status")
    notes = models.TextField(blank=True, verbose_name="Notes")
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Total Price")
    attachment = models.FileField(upload_to='booking_attachments/', blank=True, null=True, verbose_name="Attachment")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.booking_code == 'TEMP':
            self.booking_code = f"BK{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.booking_code} - {self.user.username} - {self.room.name}"

    class Meta:
        verbose_name = "Booking"
        verbose_name_plural = "Bookings"
        unique_together = ['room', 'booking_date', 'start_time', 'end_time']


class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('transfer', 'Bank Transfer'),
        ('card', 'Credit Card'),
        ('gateway', 'Payment Gateway'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('refunding', 'Refund Processing'),
        ('refunded', 'Refunded (Completed)'),
    ]

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment', verbose_name="Booking")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Amount")
    method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, verbose_name="Payment Method")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Status")
    proof = models.ImageField(upload_to='payment_proofs/', blank=True, null=True, verbose_name="Payment Proof")
    notes = models.TextField(blank=True, verbose_name="Notes")
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_payments', limit_choices_to={'is_staff': True}, verbose_name="Verified By")
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name="Verification Time")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.booking.booking_code} - {self.status}"

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"


class Invoice(models.Model):
    invoice_number = models.CharField(max_length=50, unique=True, default='TEMP', verbose_name="Invoice Number")
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='invoice', verbose_name="Booking")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Amount")
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Tax")
    total = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Total")
    description = models.TextField(blank=True, verbose_name="Description")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.invoice_number == 'TEMP':
            self.invoice_number = f"INV{timezone.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.invoice_number

    class Meta:
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"


# ==================== NOTIFICATIONS ====================
class Notification(models.Model):
    TYPE_CHOICES = [
        ('booking_pending', 'Booking Pending'),
        ('booking_approved', 'Booking Approved'),
        ('booking_rejected', 'Booking Rejected'),
        ('booking_cancelled', 'Booking Cancelled'),
        ('payment_reminder', 'Payment Reminder'),
        ('payment_verified', 'Payment Verified'),
        ('payment_rejected', 'Payment Rejected'),
    ]

    CHANNEL_CHOICES = [
        ('in_app', 'In-App'),
        ('email', 'Email'),
        ('sms', 'SMS'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name="User")
    type = models.CharField(max_length=30, choices=TYPE_CHOICES, verbose_name="Type")
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='in_app', verbose_name="Channel")
    title = models.CharField(max_length=200, verbose_name="Title")
    message = models.TextField(verbose_name="Message")
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications', verbose_name="Booking")
    is_read = models.BooleanField(default=False, verbose_name="Is Read")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="Read At")
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name="Sent At")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_type_display()}"

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']


class NotificationPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences', verbose_name="User")
    email_notifications = models.BooleanField(default=True, verbose_name="Email Notifications")
    sms_notifications = models.BooleanField(default=False, verbose_name="SMS Notifications")
    in_app_notifications = models.BooleanField(default=True, verbose_name="In-App Notifications")
    booking_status_updates = models.BooleanField(default=True, verbose_name="Booking Status Updates")
    payment_reminders = models.BooleanField(default=True, verbose_name="Payment Reminders")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Notification Preference {self.user.username}"

    class Meta:
        verbose_name = "Notification Preference"
        verbose_name_plural = "Notification Preferences"


# ==================== REVIEWS & RATINGS ====================
class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews', verbose_name="User")
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='reviews', verbose_name="Room")
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name='review', verbose_name="Booking")
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Rating"
    )
    comment = models.TextField(blank=True, verbose_name="Comment")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Review {self.user.username} for {self.room.name}"

    class Meta:
        verbose_name = "Review"
        verbose_name_plural = "Reviews"
        unique_together = ['user', 'room']

