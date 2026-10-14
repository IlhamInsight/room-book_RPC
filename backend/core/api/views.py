from rest_framework import viewsets, status, permissions, filters, parsers
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth.models import User
from django.db.models import Q, Avg
from django_filters.rest_framework import DjangoFilterBackend
from datetime import datetime, timedelta

from core.models import (
    UserProfile, Room, AmenityType, BlackoutDate,
    Booking, Payment, Invoice, Notification, NotificationPreference,
    Review
)
from .serializers import (
    UserProfileSerializer, UserDetailSerializer, UserRegisterSerializer,
    ChangePasswordSerializer, AmenityTypeSerializer,
    BlackoutDateSerializer, RoomListSerializer, RoomDetailSerializer,
    BookingListSerializer, BookingDetailSerializer, BookingCreateSerializer,
    PaymentSerializer, InvoiceSerializer, NotificationSerializer,
    NotificationPreferenceSerializer, ReviewSerializer
)


# ==================== AUTH VIEWS ====================
class UserRegisterView(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def register(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'user': UserDetailSerializer(user).data,
                'message': 'User berhasil didaftarkan'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Endpoint untuk login yang mengembalikan access & refresh token
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            username = request.data.get('username')
            # Look up using username OR email to handle synced/unsynced emails robustly
            try:
                user = User.objects.get(Q(username__iexact=username) | Q(email__iexact=username))
                response.data['user'] = UserDetailSerializer(user, context={'request': request}).data
            except User.DoesNotExist:
                pass
        return response


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def change_password(request):
    serializer = ChangePasswordSerializer(data=request.data)
    if serializer.is_valid():
        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {'old_password': 'Password lama tidak benar.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({'message': 'Password berhasil diubah.'})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ==================== USER PROFILE ====================
class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    @action(detail=False, methods=['get'])
    def my_profile(self, request):
        from .serializers import UserDetailSerializer
        serializer = UserDetailSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        profile = request.user.profile
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        
        user_updated = False
        user = request.user
        
        if 'full_name' in request.data:
            profile.full_name = request.data['full_name']
            profile.save()
            user_updated = True # Trigger user save/refresh if needed, though here we just need to return
        if 'email' in request.data:
            new_email = request.data['email']
            # Check if email is already taken by another user
            if User.objects.filter(Q(username__iexact=new_email) | Q(email__iexact=new_email)).exclude(pk=user.pk).exists():
                return Response(
                    {'email': 'Email ini sudah digunakan oleh pengguna lain.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.email = new_email
            user.username = new_email  # Sync username with new email address
            user_updated = True
            
        if user_updated:
            user.save()
            
        if serializer.is_valid():
            serializer.save()
            
            # Return updated user details similar to login response
            from .serializers import UserDetailSerializer
            return Response(UserDetailSerializer(user, context={'request': request}).data)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ==================== ROOM MANAGEMENT ====================
class AmenityTypeViewSet(viewsets.ModelViewSet):
    queryset = AmenityType.objects.all()
    serializer_class = AmenityTypeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]




class BlackoutDateViewSet(viewsets.ModelViewSet):
    queryset = BlackoutDate.objects.all()
    serializer_class = BlackoutDateSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['room', 'date']


class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'is_available', 'location', 'amenities', 'capacity']
    search_fields = ['name', 'description', 'location']
    ordering_fields = ['price_per_hour', 'capacity', 'created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return RoomDetailSerializer
        return RoomListSerializer

    @action(detail=True, methods=['get'])
    def check_availability(self, request, pk=None):
        """
        Check ketersediaan ruangan pada tanggal & waktu tertentu
        Query params: date (YYYY-MM-DD), start_time, end_time
        """
        room = self.get_object()
        booking_date = request.query_params.get('date')
        start_time = request.query_params.get('start_time')
        end_time = request.query_params.get('end_time')

        if not all([booking_date, start_time, end_time]):
            return Response(
                {'error': 'Mohon sediakan date, start_time, end_time'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            booking_date = datetime.strptime(booking_date, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Format date harus YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check blackout dates
        if BlackoutDate.objects.filter(room=room, date=booking_date).exists():
            return Response({
                'available': False,
                'reason': 'Ruangan libur pada tanggal ini'
            })

        # All rooms are considered available unless a blackout date exists.
        # Skipping day‑of‑week availability checks.

        # Check conflicting bookings
        conflicts = Booking.objects.filter(
            room=room,
            booking_date=booking_date,
            status__in=['approved', 'pending']
        ).exclude(status__in=['rejected', 'cancelled'])

        # Check time conflicts
        start_dt = datetime.combine(booking_date, datetime.strptime(start_time, '%H:%M').time())
        end_dt = datetime.combine(booking_date, datetime.strptime(end_time, '%H:%M').time())

        for booking in conflicts:
            booking_start = datetime.combine(booking_date, booking.start_time)
            booking_end = datetime.combine(booking_date, booking.end_time)

            if not (end_dt <= booking_start or start_dt >= booking_end):
                return Response({
                    'available': False,
                    'reason': f'Ruangan sudah dipesan dari {booking.start_time} hingga {booking.end_time}'
                })

        return Response({'available': True})


# ==================== BOOKING ====================
class BookingViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'room', 'booking_date']
    ordering_fields = ['booking_date', 'created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return BookingCreateSerializer
        elif self.action == 'retrieve':
            return BookingDetailSerializer
        return BookingListSerializer

    def get_queryset(self):
        user = self.request.user
        if user.profile.role == 'admin':
            return Booking.objects.all()
        return Booking.objects.filter(user=user)

    def perform_create(self, serializer):
        # The user is already set in serializer.save() or validate
        booking = serializer.save()
        
        # Create notification for user
        Notification.objects.create(
            user=self.request.user,
            type='booking_pending',
            title='Booking Berhasil Dibuat',
            message=f'Booking Anda untuk {booking.room.name} sedang menunggu persetujuan.',
            booking=booking
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Auto-generate missing invoice if approved
        from decimal import Decimal
        if instance.status in ['approved', 'completed'] and not hasattr(instance, 'invoice'):
            amount = instance.total_price
            tax = amount * Decimal('0.11')
            total = amount + tax
            Invoice.objects.create(
                booking=instance,
                amount=amount,
                tax=tax,
                total=total,
                description=f'Booking {instance.room.name} ({instance.booking_date})'
            )
            # Refresh instance to get the newly created invoice
            instance.refresh_from_db()
            
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_bookings(self, request):
        bookings = Booking.objects.filter(user=request.user)
        
        # Check and create missing invoices for approved bookings in the list
        from decimal import Decimal
        for b in bookings:
            if b.status in ['approved', 'completed'] and not hasattr(b, 'invoice'):
                amount = b.total_price
                tax = amount * Decimal('0.11')
                total = amount + tax
                Invoice.objects.create(
                    booking=b,
                    amount=amount,
                    tax=tax,
                    total=total,
                    description=f'Booking {b.room.name} ({b.booking_date})'
                )
        
        # Re-fetch or refresh to get invoices
        bookings = Booking.objects.filter(user=request.user)
        serializer = self.get_serializer(bookings, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        if booking.status in ['completed', 'cancelled']:
            return Response(
                {'error': 'Booking tidak dapat dibatalkan'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_status = booking.status
        booking.status = 'cancelled'
        booking.save()

        # Handle Refund Logic
        refund_info = ""
        notif_title = "Booking Dibatalkan"
        
        if hasattr(booking, 'payment'):
            if old_status == 'approved':
                # Needs admin approval for refund
                booking.payment.status = 'refunding'
                booking.payment.save()
                refund_info = " Pengembalian dana sedang diproses oleh admin."
                notif_title = "Booking Dibatalkan & Refund Diproses"
            else:
                # Automatic/Direct refund for pending
                booking.payment.status = 'refunded'
                booking.payment.save()
                refund_info = " Pengembalian dana selesai."
                notif_title = "Booking Dibatalkan & Refund Selesai"

        # Create notification
        Notification.objects.create(
            user=booking.user,
            type='booking_cancelled',
            title=notif_title,
            message=f'Booking Anda untuk {booking.room.name} telah dibatalkan.{refund_info}',
            booking=booking
        )

        return Response({'message': f'Booking berhasil dibatalkan.{refund_info}'})

    def perform_destroy(self, instance):
        user = instance.user
        room_name = instance.room.name
        booking_code = instance.booking_code
        
        instance.delete()
        
        # Create notification about deletion
        Notification.objects.create(
            user=user,
            type='booking_cancelled',
            title='Booking Dihapus',
            message=f'Booking {booking_code} untuk {room_name} telah dihapus dari sistem.',
        )


# ==================== PAYMENT ====================
class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['booking', 'status', 'method']

    def get_queryset(self):
        user = self.request.user
        if user.profile.role == 'admin':
            return Payment.objects.all()
        return Payment.objects.filter(booking__user=user)

    def perform_create(self, serializer):
        # Automatically set amount from booking total price
        booking = serializer.validated_data.get('booking')
        payment = serializer.save(amount=booking.total_price)
        
        # Create notification for user
        Notification.objects.create(
            user=payment.booking.user,
            type='payment_reminder',
            title='Pembayaran Diterima',
            message=f'Pembayaran untuk booking {payment.booking.booking_code} telah diterima dan sedang menunggu verifikasi.',
            booking=payment.booking
        )

# ==================== INVOICE ====================
class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['booking']

    def get_queryset(self):
        user = self.request.user
        if user.profile.role == 'admin':
            return Invoice.objects.all()
        return Invoice.objects.filter(booking__user=user)


# ==================== NOTIFICATIONS ====================
class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['type', 'is_read']
    ordering = ['-created_at']

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.read_at = datetime.now()
        notification.save()
        return Response({'message': 'Notifikasi ditandai sudah dibaca'})

    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True,
            read_at=datetime.now()
        )
        return Response({'message': 'Semua notifikasi ditandai sudah dibaca'})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({'unread_count': count})


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    queryset = NotificationPreference.objects.all()
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def my_preferences(self, request):
        preferences = request.user.notification_preferences
        serializer = self.get_serializer(preferences)
        return Response(serializer.data)

    @action(detail=False, methods=['put', 'patch'])
    def update_preferences(self, request):
        preferences = request.user.notification_preferences
        serializer = self.get_serializer(preferences, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ==================== REVIEWS ====================
class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['room']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)