from django.contrib import admin
from django.utils.html import format_html
from .models import (
    UserProfile, AmenityType, Room, BlackoutDate, Booking,
    Payment, Invoice, Notification, NotificationPreference, Review
)
from unfold.admin import ModelAdmin, StackedInline
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RelatedDropdownFilter, DropdownFilter, ChoicesRadioFilter, RangeDateFilter, RangeNumericFilter
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User


# ==================== USER & PROFILE ====================
class UserProfileInline(StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Full Profiles'
    fk_name = 'user'

# Unregister default User Admin
admin.site.unregister(User)

@admin.register(User)
class CustomUserAdmin(BaseUserAdmin, ModelAdmin):
    inlines = (UserProfileInline, )
    list_display = ('email', 'get_full_name', 'get_role', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    
    def get_full_name(self, obj):
        try:
            return obj.profile.full_name
        except:
            return "-"
    get_full_name.short_description = 'Full Name'

    def get_role(self, obj):
        try:
            return obj.profile.get_role_display()
        except:
            return "-"
    get_role.short_description = 'Role'

    # Menghapus first_name dan last_name dari tampilan edit
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Informasi Pribadi', {'fields': ('email',)}),
        ('Hak Akses', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Waktu Penting', {'fields': ('last_login', 'date_joined')}),
    )
    
    readonly_fields = ('username',)

@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
    list_display = ('user', 'full_name', 'role', 'phone_number', 'is_email_verified')
    list_filter = ('role', 'is_email_verified', 'created_at')
    search_fields = ('user__username', 'user__email', 'phone_number')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('User Info', {
            'fields': ('user', 'role', 'is_email_verified')
        }),
        ('Personal Info', {
            'fields': ('full_name', 'phone_number', 'address', 'avatar')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# ==================== ROOM & AMENITIES ====================
@admin.register(AmenityType)
class AmenityTypeAdmin(ModelAdmin):
    list_display = ('name', 'icon', 'description')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at',)


@admin.register(Room)
class RoomAdmin(ModelAdmin):
    list_display = ('name', 'location', 'capacity', 'price_per_hour', 'status', 'is_available', 'rating_display')
    list_filter = (
        'status',
        'is_available',
        'capacity',
        'location',
        'created_at',
    )
    search_fields = ('name', 'description', 'location')
    readonly_fields = ('created_at', 'updated_at', 'rating_display')
    fieldsets = (
        ('Room Info', {
            'fields': ('name', 'location', 'capacity', 'description')
        }),
        ('Pricing & Availability', {
            'fields': ('price_per_hour', 'is_available', 'status')
        }),
        ('Facilities', {
            'fields': ('amenities',)
        }),
        ('Media', {
            'fields': ('image',)
        }),
        ('Rating', {
            'fields': ('rating_display',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    filter_horizontal = ('amenities',)

    def rating_display(self, obj):
        reviews = obj.reviews.all()
        if reviews:
            avg = sum(r.rating for r in reviews) / len(reviews)
            return f"{avg:.1f}/5 ({len(reviews)} reviews)"
        return "No reviews yet"
    rating_display.short_description = "Rating"




@admin.register(BlackoutDate)
class BlackoutDateAdmin(ModelAdmin):
    list_display = ('room', 'date', 'reason')
    list_filter = ('room', 'date')
    search_fields = ('room__name', 'reason')
    readonly_fields = ('created_at',)


# ==================== BOOKING & PAYMENTS ====================
@admin.register(Booking)
class BookingAdmin(ModelAdmin):
    list_display = ('booking_code', 'user', 'room', 'booking_date', 'time_display', 'status_badge', 'total_price')
    list_filter = (
        'status',
        'booking_date',
        ('room', RelatedDropdownFilter),
        ('user', RelatedDropdownFilter),
    )
    search_fields = ('user__username', 'room__name', 'booking_code', 'notes')
    readonly_fields = ('booking_code', 'total_price', 'created_at', 'updated_at')
    fieldsets = (
        ('Booking Info', {
            'fields': ('booking_code', 'user', 'room', 'status')
        }),
        ('Date & Time', {
            'fields': ('booking_date', 'start_time', 'end_time')
        }),
        ('Payment Info', {
            'fields': ('total_price', 'attachment')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    raw_id_fields = ('user', 'room')
    actions = ['mark_pending', 'mark_approved', 'mark_rejected', 'mark_cancelled', 'mark_completed']

    def time_display(self, obj):
        return f"{obj.start_time} - {obj.end_time}"
    time_display.short_description = "Time"

    def status_badge(self, obj):
        colors = {
            'pending': {'bg': '#F59E0B', 'fg': '#FFFFFF'},   # Solid Amber
            'approved': {'bg': '#10B981', 'fg': '#FFFFFF'},  # Solid Emerald
            'rejected': {'bg': '#EF4444', 'fg': '#FFFFFF'},  # Solid Red
            'cancelled': {'bg': '#6B7280', 'fg': '#FFFFFF'}, # Solid Gray
            'completed': {'bg': '#3B82F6', 'fg': '#FFFFFF'}, # Solid Blue
        }
        status_style = colors.get(obj.status, {'bg': '#F3F4F6', 'fg': '#4B5563'})
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 4px 12px; border-radius: 9999px; font-weight: 600; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em;">{}</span>',
            status_style['bg'],
            status_style['fg'],
            obj.get_status_display()
        )
    status_badge.short_description = "Status"

    def mark_pending(self, request, queryset):
        count = queryset.update(status='pending')
        self.message_user(request, f"Successfully marked {count} bookings as Pending.")
    mark_pending.short_description = "Pending"

    def mark_approved(self, request, queryset):
        count = 0
        from decimal import Decimal
        from core.models import Notification, Invoice
        from datetime import datetime
        
        for booking in queryset:
            if booking.status != 'approved':
                booking.status = 'approved'
                booking.save()
                
                # Update payment status if exists
                if hasattr(booking, 'payment'):
                    payment = booking.payment
                    if payment.status == 'pending':
                        payment.status = 'verified'
                        payment.verified_by = request.user
                        payment.verified_at = datetime.now()
                        payment.save()
                
                # Generate Invoice
                if not hasattr(booking, 'invoice'):
                    amount = booking.total_price
                    tax = amount * Decimal('0.11')
                    total = amount + tax
                    Invoice.objects.create(
                        booking=booking,
                        amount=amount,
                        tax=tax,
                        total=total,
                        description=f'Booking {booking.room.name} ({booking.booking_date})'
                    )
                
                # Create notification
                Notification.objects.create(
                    user=booking.user,
                    type='booking_approved',
                    title='Booking Approved',
                    message=f'Your booking for {booking.room.name} has been approved!',
                    booking=booking
                )
                count += 1
        self.message_user(request, f"Successfully approved {count} bookings.")
    mark_approved.short_description = "Approved"

    def mark_rejected(self, request, queryset):
        count = 0
        from core.models import Notification
        from datetime import datetime
        
        for booking in queryset:
            if booking.status not in ['rejected', 'cancelled', 'completed']:
                booking.status = 'rejected'
                booking.save()
                
                # Update payment status if exists
                if hasattr(booking, 'payment'):
                    payment = booking.payment
                    if payment.status == 'pending':
                        payment.status = 'rejected'
                        payment.verified_by = request.user
                        payment.verified_at = datetime.now()
                        payment.save()
                
                refund_info = ""
                if hasattr(booking, 'payment'):
                    refund_info = " Your refund will be processed shortly."
                
                # Create notification
                Notification.objects.create(
                    user=booking.user,
                    type='booking_rejected',
                    title='Booking Rejected',
                    message=f'Your booking for {booking.room.name} has been rejected.{refund_info}',
                    booking=booking
                )
                count += 1
        self.message_user(request, f"Successfully rejected {count} bookings.")
    mark_rejected.short_description = "Rejected"

    def mark_cancelled(self, request, queryset):
        count = 0
        from core.models import Notification
        
        for booking in queryset:
            if booking.status not in ['completed', 'cancelled']:
                old_status = booking.status
                booking.status = 'cancelled'
                booking.save()
                
                refund_info = ""
                notif_title = "Booking Cancelled"
                
                if hasattr(booking, 'payment'):
                    if old_status == 'approved':
                        booking.payment.status = 'refunding'
                        booking.payment.save()
                        refund_info = " Refund is being processed by the admin."
                        notif_title = "Booking Cancelled & Refund Processed"
                    else:
                        booking.payment.status = 'refunded'
                        booking.payment.save()
                        refund_info = " Refund completed."
                        notif_title = "Booking Cancelled & Refund Completed"
                
                Notification.objects.create(
                    user=booking.user,
                    type='booking_cancelled',
                    title=notif_title,
                    message=f'Your booking for {booking.room.name} has been cancelled.{refund_info}',
                    booking=booking
                )
                count += 1
        self.message_user(request, f"Successfully cancelled {count} bookings.")
    mark_cancelled.short_description = "Cancelled"

    def mark_completed(self, request, queryset):
        count = 0
        from core.models import Notification
        from datetime import datetime
        
        for booking in queryset:
            if booking.status == 'approved':
                booking.status = 'completed'
                booking.save()
                
                # Ensure payment is verified when completed
                if hasattr(booking, 'payment'):
                    payment = booking.payment
                    if payment.status != 'verified':
                        payment.status = 'verified'
                        if not payment.verified_by:
                            payment.verified_by = request.user
                            payment.verified_at = datetime.now()
                        payment.save()
                
                Notification.objects.create(
                    user=booking.user,
                    type='booking_completed',
                    title='Booking Completed',
                    message=f'Thank you for using {booking.room.name}. Please leave a review!',
                    booking=booking
                )
                count += 1
        self.message_user(request, f"Successfully completed {count} bookings.")
    mark_completed.short_description = "Completed"


@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    list_display = ('booking', 'amount', 'method', 'status_badge', 'get_verified_by', 'created_at')
    list_filter = (
        'status',
        'method',
        'created_at',
        ('verified_by', RelatedDropdownFilter),
    )
    search_fields = ('booking__booking_code', 'booking__user__username')
    readonly_fields = ('created_at', 'updated_at', 'verified_at')
    fieldsets = (
        ('Payment Info', {
            'fields': ('booking', 'amount', 'method', 'status')
        }),
        ('Proof', {
            'fields': ('proof',)
        }),
        ('Verification', {
            'fields': ('verified_by', 'verified_at', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    raw_id_fields = ('booking', 'verified_by')
    actions = ['mark_pending', 'verify_payment', 'mark_refunding', 'mark_refunded']

    def get_verified_by(self, obj):
        if obj.verified_by:
            return f"{obj.verified_by.profile.full_name} ({obj.verified_by.username})" if obj.verified_by.profile.full_name else obj.verified_by.username
        return "-"
    get_verified_by.short_description = "Verified By"

    def status_badge(self, obj):
        colors = {
            'pending': {'bg': '#F59E0B', 'fg': '#FFFFFF'},   # Solid Amber
            'verified': {'bg': '#10B981', 'fg': '#FFFFFF'},  # Solid Emerald
            'rejected': {'bg': '#EF4444', 'fg': '#FFFFFF'},  # Solid Red
            'refunding': {'bg': '#6366F1', 'fg': '#FFFFFF'}, # Solid Indigo
            'refunded': {'bg': '#3B82F6', 'fg': '#FFFFFF'},  # Solid Blue
        }
        status_style = colors.get(obj.status, {'bg': '#F3F4F6', 'fg': '#4B5563'})
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 4px 12px; border-radius: 9999px; font-weight: 600; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em;">{}</span>',
            status_style['bg'],
            status_style['fg'],
            obj.get_status_display()
        )
    status_badge.short_description = "Status"

    def mark_pending(self, request, queryset):
        count = queryset.update(status='pending')
        self.message_user(request, f"Successfully marked {count} payments as Pending Payment.")
    mark_pending.short_description = "Pending Payment"

    def mark_refunding(self, request, queryset):
        count = queryset.update(status='refunding')
        self.message_user(request, f"Successfully marked {count} payments as Refund Processing.")
    mark_refunding.short_description = "Refund Processing"

    def mark_refunded(self, request, queryset):
        count = queryset.update(status='refunded')
        self.message_user(request, f"Successfully marked {count} payments as Refunded (Completed).")
    mark_refunded.short_description = "Refunded (Completed)"

    def verify_payment(self, request, queryset):
        count = 0
        from decimal import Decimal
        from core.models import Notification, Invoice
        from datetime import datetime
        
        for payment in queryset:
            if payment.status != 'verified':
                payment.status = 'verified'
                payment.verified_by = request.user
                payment.verified_at = datetime.now()
                payment.save()
                
                # Update booking status to approved
                payment.booking.status = 'approved'
                payment.booking.save()
                
                # Auto-generate Invoice
                if not hasattr(payment.booking, 'invoice'):
                    amount = payment.amount
                    tax = amount * Decimal('0.11')  # PPN 11%
                    total = amount + tax
                    Invoice.objects.create(
                        booking=payment.booking,
                        amount=amount,
                        tax=tax,
                        total=total,
                        description=f'Room booking {payment.booking.room.name} on {payment.booking.booking_date} ({payment.booking.start_time}-{payment.booking.end_time})'
                    )
                
                # Create notification
                Notification.objects.create(
                    user=payment.booking.user,
                    type='payment_verified',
                    title='Payment Verified',
                    message='Your payment has been verified. Your booking is confirmed!',
                    booking=payment.booking
                )
                count += 1
        self.message_user(request, f"Successfully verified {count} payments.")
    verify_payment.short_description = "Verified"

    def reject_payment(self, request, queryset):
        count = 0
        from core.models import Notification
        from datetime import datetime
        
        for payment in queryset:
            if payment.status != 'rejected':
                payment.status = 'rejected'
                payment.verified_by = request.user
                payment.verified_at = datetime.now()
                payment.save()
                
                # Create notification
                Notification.objects.create(
                    user=payment.booking.user,
                    type='payment_rejected',
                    title='Payment Rejected',
                    message='Your payment has been rejected. Please upload a valid payment proof.',
                    booking=payment.booking
                )
                count += 1
        self.message_user(request, f"Successfully rejected {count} payments.")
    reject_payment.short_description = "Rejected"


@admin.register(Invoice)
class InvoiceAdmin(ModelAdmin):
    list_display = ('invoice_number', 'booking', 'total', 'created_at')
    list_filter = ('created_at', 'booking__room')
    search_fields = ('invoice_number', 'booking__booking_code')
    readonly_fields = ('invoice_number', 'created_at', 'updated_at')
    fieldsets = (
        ('Invoice Info', {
            'fields': ('invoice_number', 'booking')
        }),
        ('Amount', {
            'fields': ('amount', 'tax', 'total')
        }),
        ('Description', {
            'fields': ('description',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    raw_id_fields = ('booking',)


# ==================== NOTIFICATIONS ====================
@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = ('user', 'type', 'title', 'channel', 'is_read', 'sent_at')
    list_filter = ('type', 'channel', 'is_read', 'sent_at')
    search_fields = ('user__username', 'title', 'message')
    readonly_fields = ('sent_at', 'created_at')
    fieldsets = (
        ('Notification Info', {
            'fields': ('user', 'type', 'channel')
        }),
        ('Content', {
            'fields': ('title', 'message')
        }),
        ('Status', {
            'fields': ('is_read', 'read_at', 'booking')
        }),
        ('Timestamps', {
            'fields': ('sent_at', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    raw_id_fields = ('user', 'booking')


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(ModelAdmin):
    list_display = ('user', 'email_notifications', 'sms_notifications', 'in_app_notifications')
    list_filter = ('email_notifications', 'sms_notifications', 'in_app_notifications')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')


# ==================== REVIEWS ====================
@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = ('user', 'room', 'rating_stars', 'created_at')
    list_filter = (
        'rating',
        ('room', RelatedDropdownFilter),
        'created_at',
    )
    search_fields = ('user__username', 'room__name', 'comment')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Review Info', {
            'fields': ('user', 'room', 'booking')
        }),
        ('Rating & Comment', {
            'fields': ('rating', 'comment')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    raw_id_fields = ('user', 'room', 'booking')

    def rating_stars(self, obj):
        stars = '⭐' * obj.rating
        return f"{stars} ({obj.rating}/5)"
    rating_stars.short_description = "Rating"
