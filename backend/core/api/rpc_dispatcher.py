import json
import base64
from datetime import datetime, timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.db.models import Q, Avg
from django.core.files.base import ContentFile
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from core.models import (
    UserProfile, Room, AmenityType, BlackoutDate,
    Booking, Payment, Invoice, Notification, NotificationPreference,
    Review
)
from .serializers import (
    UserDetailSerializer, UserRegisterSerializer,
    RoomListSerializer, RoomDetailSerializer,
    AmenityTypeSerializer, BookingListSerializer, BookingDetailSerializer,
    PaymentSerializer, InvoiceSerializer, NotificationSerializer,
    ReviewSerializer
)

class JSONRPCError(Exception):
    def __init__(self, code, message, data=None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)


class RPCDispatcher:
    def __init__(self):
        self.registry = {}
        self._register_methods()

    def register(self, name, func):
        self.registry[name] = func

    def _get_user_from_token(self, token_str):
        if not token_str:
            return None
        if token_str.startswith('Bearer '):
            token_str = token_str[7:].strip()
        try:
            token = AccessToken(token_str)
            user_id = token.payload.get('user_id')
            return User.objects.filter(id=user_id).first()
        except (InvalidToken, TokenError, Exception):
            return None

    def _extract_auth_user(self, request_meta, params):
        # 1. From Authorization header
        auth_header = request_meta.get('HTTP_AUTHORIZATION') or request_meta.get('Authorization') or ''
        user = self._get_user_from_token(auth_header)
        if user:
            return user
        
        # 2. From params token
        token_in_params = params.get('token') if isinstance(params, dict) else None
        if token_in_params:
            user = self._get_user_from_token(token_in_params)
            if user:
                return user
        return None

    def _require_auth(self, user):
        if not user or not user.is_authenticated:
            raise JSONRPCError(-32001, "Unauthorized: Authentication required")

    def _register_methods(self):
        # Auth procedures
        self.register('auth.login', self._auth_login)
        self.register('auth.register', self._auth_register)
        self.register('auth.get_profile', self._auth_get_profile)
        self.register('auth.update_profile', self._auth_update_profile)
        self.register('auth.change_password', self._auth_change_password)

        # Room procedures
        self.register('room.get_list', self._room_get_list)
        self.register('room.get_detail', self._room_get_detail)
        self.register('room.get_amenities', self._room_get_amenities)
        self.register('room.check_availability', self._room_check_availability)

        # Booking procedures
        self.register('booking.create', self._booking_create)
        self.register('booking.get_my_bookings', self._booking_get_my_bookings)
        self.register('booking.get_detail', self._booking_get_detail)
        self.register('booking.cancel', self._booking_cancel)

        # Payment & Invoice procedures
        self.register('payment.submit', self._payment_submit)
        self.register('invoice.get_detail', self._invoice_get_detail)

        # Reviews procedures
        self.register('review.get_list', self._review_get_list)
        self.register('review.create', self._review_create)

        # Notification procedures
        self.register('notification.get_unread_count', self._notification_get_unread_count)
        self.register('notification.get_list', self._notification_get_list)
        self.register('notification.mark_as_read', self._notification_mark_as_read)
        self.register('notification.mark_all_as_read', self._notification_mark_all_as_read)

    # ================= Procedures Implementation =================

    def _auth_login(self, params, user, context):
        username = params.get('username')
        password = params.get('password')
        if not username or not password:
            raise JSONRPCError(-32602, "Username/email and password required")

        user_obj = User.objects.filter(Q(username__iexact=username) | Q(email__iexact=username)).first()
        if not user_obj or not user_obj.check_password(password):
            raise JSONRPCError(-32001, "Invalid username or password")

        refresh = RefreshToken.for_user(user_obj)
        user_data = UserDetailSerializer(user_obj, context=context).data
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': user_data
        }

    def _auth_register(self, params, user, context):
        serializer = UserRegisterSerializer(data=params)
        if serializer.is_valid():
            new_user = serializer.save()
            return {
                'user': UserDetailSerializer(new_user, context=context).data,
                'message': 'User berhasil didaftarkan'
            }
        errors = "; ".join([f"{k}: {', '.join(v)}" for k, v in serializer.errors.items()])
        raise JSONRPCError(-32602, f"Validation error: {errors}", serializer.errors)

    def _auth_get_profile(self, params, user, context):
        self._require_auth(user)
        return UserDetailSerializer(user, context=context).data

    def _auth_update_profile(self, params, user, context):
        self._require_auth(user)
        profile = user.profile
        
        full_name = params.get('full_name') or params.get('name')
        if full_name:
            profile.full_name = full_name
            profile.save()

        email = params.get('email')
        if email and email != user.email:
            if User.objects.filter(Q(username__iexact=email) | Q(email__iexact=email)).exclude(pk=user.pk).exists():
                raise JSONRPCError(-32602, "Email ini sudah digunakan oleh pengguna lain.")
            user.email = email
            user.username = email
            user.save()

        phone_number = params.get('phone_number') or params.get('phone')
        if phone_number is not None:
            profile.phone_number = phone_number
        address = params.get('address')
        if address is not None:
            profile.address = address

        # Handle avatar (base64) if sent via JSON
        avatar_data = params.get('avatar_base64') or params.get('avatar')
        if avatar_data and isinstance(avatar_data, str) and (';base64,' in avatar_data or avatar_data.startswith('data:image')):
            try:
                if ';base64,' in avatar_data:
                    header, imgstr = avatar_data.split(';base64,')
                    ext = header.split('/')[-1] if '/' in header else 'jpg'
                else:
                    imgstr = avatar_data
                    ext = 'jpg'
                file_name = f"avatar_{user.id}_{int(datetime.now().timestamp())}.{ext}"
                profile.avatar = ContentFile(base64.b64decode(imgstr), name=file_name)
            except Exception as e:
                import traceback
                traceback.print_exc()
        profile.save()
        return UserDetailSerializer(user, context=context).data

    def _auth_change_password(self, params, user, context):
        self._require_auth(user)
        old_password = params.get('old_password')
        new_password = params.get('new_password')
        if not user.check_password(old_password):
            raise JSONRPCError(-32602, "Password lama tidak benar.")
        user.set_password(new_password)
        user.save()
        return {'message': 'Password berhasil diubah.'}

    def _room_get_list(self, params, user, context):
        queryset = Room.objects.all().order_by('-created_at')
        search = params.get('search') or params.get('searchTerm')
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search) | Q(location__icontains=search))
        
        max_price = params.get('max_price') or params.get('priceRange')
        if max_price:
            try:
                queryset = queryset.filter(price_per_hour__lte=float(max_price))
            except ValueError:
                pass

        capacity = params.get('capacity')
        if capacity and isinstance(capacity, (int, str)) and str(capacity).isdigit():
            queryset = queryset.filter(capacity__gte=int(capacity))

        return RoomListSerializer(queryset, many=True, context=context).data

    def _room_get_detail(self, params, user, context):
        room_id = params.get('id') or params.get('room_id')
        try:
            room = Room.objects.get(id=room_id)
        except Room.DoesNotExist:
            raise JSONRPCError(-32602, f"Room with ID {room_id} not found")
        return RoomDetailSerializer(room, context=context).data

    def _room_get_amenities(self, params, user, context):
        amenities = AmenityType.objects.all()
        return AmenityTypeSerializer(amenities, many=True, context=context).data

    def _room_check_availability(self, params, user, context):
        room_id = params.get('room_id') or params.get('id')
        booking_date = params.get('date')
        start_time = params.get('start_time')
        end_time = params.get('end_time')

        if not all([room_id, booking_date, start_time, end_time]):
            raise JSONRPCError(-32602, "Mohon sediakan room_id, date, start_time, end_time")

        try:
            room = Room.objects.get(id=room_id)
        except Room.DoesNotExist:
            raise JSONRPCError(-32602, "Ruangan tidak ditemukan")

        try:
            b_date = datetime.strptime(booking_date, '%Y-%m-%d').date()
        except ValueError:
            raise JSONRPCError(-32602, "Format tanggal harus YYYY-MM-DD")

        try:
            st_obj = datetime.strptime(start_time, '%H:%M').time()
            et_obj = datetime.strptime(end_time, '%H:%M').time()
        except ValueError:
            raise JSONRPCError(-32602, "Format jam harus HH:MM (contoh: 09:00)")

        start_dt = datetime.combine(b_date, st_obj)
        # Jika waktu selesai lebih kecil atau sama dengan waktu mulai, berarti sewa lewat tengah malam / 24 jam penuh
        if et_obj <= st_obj:
            end_dt = datetime.combine(b_date + timedelta(days=1), et_obj)
            is_overnight = True
        else:
            end_dt = datetime.combine(b_date, et_obj)
            is_overnight = False

        duration_seconds = (end_dt - start_dt).total_seconds()

        # Validasi: Durasi minimal 30 menit (1800 detik)
        if duration_seconds < 1800:
            return {
                'available': False,
                'reason': 'Durasi pemesanan minimal adalah 30 menit'
            }

        # Validasi: Durasi maksimal 24 jam
        if duration_seconds > 86400:
            return {
                'available': False,
                'reason': 'Durasi pemesanan maksimal adalah 24 jam'
            }

        # Check blackout dates (cek kedua hari jika lewat tengah malam)
        check_dates = [b_date, end_dt.date()] if is_overnight else [b_date]
        if BlackoutDate.objects.filter(room=room, date__in=check_dates).exists():
            return {'available': False, 'reason': 'Ruangan libur/tidak tersedia pada tanggal ini'}

        # Check time conflicts
        conflicts = Booking.objects.filter(
            room=room,
            booking_date__range=[b_date - timedelta(days=1), end_dt.date()],
            status__in=['approved', 'pending']
        ).exclude(status__in=['rejected', 'cancelled'])

        for booking in conflicts:
            b_start = datetime.combine(booking.booking_date, booking.start_time)
            if booking.end_time <= booking.start_time:
                b_end = datetime.combine(booking.booking_date + timedelta(days=1), booking.end_time)
            else:
                b_end = datetime.combine(booking.booking_date, booking.end_time)

            if not (end_dt <= b_start or start_dt >= b_end):
                return {
                    'available': False,
                    'reason': f'Ruangan sudah dipesan pada {b_start.strftime("%H:%M")} hingga {b_end.strftime("%H:%M")}'
                }

        duration_hours = round(duration_seconds / 3600, 2)
        total_price = float(room.price_per_hour * Decimal(str(duration_hours)))

        return {
            'available': True,
            'reason': None,
            'is_overnight': is_overnight,
            'duration_hours': duration_hours,
            'total_price': total_price
        }

    def _booking_create(self, params, user, context):
        self._require_auth(user)
        room_id = params.get('room_id') or params.get('room')
        booking_date = params.get('date') or params.get('booking_date')
        start_time = params.get('startTime') or params.get('start_time')
        end_time = params.get('endTime') or params.get('end_time')
        notes = params.get('notes', '')
        payment_method = params.get('paymentMethod', 'transfer')

        if not all([room_id, booking_date, start_time, end_time]):
            raise JSONRPCError(-32602, "Mohon lengkapi semua field: ruangan, tanggal, waktu mulai, dan waktu selesai")

        try:
            room = Room.objects.get(id=room_id)
        except Room.DoesNotExist:
            raise JSONRPCError(-32602, "Ruangan tidak ditemukan")

        try:
            b_date = datetime.strptime(booking_date, '%Y-%m-%d').date()
        except ValueError:
            raise JSONRPCError(-32602, "Format tanggal tidak valid (YYYY-MM-DD)")

        try:
            st_obj = datetime.strptime(start_time, '%H:%M').time()
            et_obj = datetime.strptime(end_time, '%H:%M').time()
        except ValueError:
            raise JSONRPCError(-32602, "Format jam tidak valid (HH:MM)")

        start_dt = datetime.combine(b_date, st_obj)
        # Jika waktu selesai lebih kecil atau sama dengan waktu mulai -> pemesanan lewat tengah malam / 24 jam penuh
        if et_obj <= st_obj:
            end_dt = datetime.combine(b_date + timedelta(days=1), et_obj)
            is_overnight = True
        else:
            end_dt = datetime.combine(b_date, et_obj)
            is_overnight = False

        duration_seconds = (end_dt - start_dt).total_seconds()

        # Validasi durasi minimal 30 menit
        if duration_seconds < 1800:
            raise JSONRPCError(-32602, "Durasi pemesanan minimal adalah 30 menit")

        # Validasi durasi maksimal 24 jam
        if duration_seconds > 86400:
            raise JSONRPCError(-32602, "Durasi pemesanan maksimal adalah 24 jam")

        # Validasi tanggal tidak boleh di masa lalu
        now_dt = datetime.now()
        if start_dt < now_dt - timedelta(minutes=5):
            raise JSONRPCError(-32602, "Waktu booking tidak boleh di masa lalu")

        # Validasi tanggal libur (Blackout date)
        check_dates = [b_date, end_dt.date()] if is_overnight else [b_date]
        if BlackoutDate.objects.filter(room=room, date__in=check_dates).exists():
            raise JSONRPCError(-32602, "Ruangan libur/tidak beroperasi pada tanggal tersebut")

        # Validasi jadwal bentrok (Conflict check)
        conflicts = Booking.objects.filter(
            room=room,
            booking_date__range=[b_date - timedelta(days=1), end_dt.date()],
            status__in=['approved', 'pending']
        ).exclude(status__in=['rejected', 'cancelled'])

        for conflict in conflicts:
            c_start = datetime.combine(conflict.booking_date, conflict.start_time)
            if conflict.end_time <= conflict.start_time:
                c_end = datetime.combine(conflict.booking_date + timedelta(days=1), conflict.end_time)
            else:
                c_end = datetime.combine(conflict.booking_date, conflict.end_time)

            if not (end_dt <= c_start or start_dt >= c_end):
                raise JSONRPCError(-32602, f"Ruangan sudah dipesan pada jam {c_start.strftime('%H:%M')} - {c_end.strftime('%H:%M')}")

        # Perhitungan durasi dalam jam (presisi desimal)
        duration_hours = Decimal(str(round(duration_seconds / 3600, 2)))
        total_price = room.price_per_hour * duration_hours

        booking = Booking.objects.create(
            user=user,
            room=room,
            booking_date=b_date,
            start_time=st_obj,
            end_time=et_obj,
            total_price=total_price,
            notes=notes,
            status='pending'
        )

        overnight_info = " (24 Jam Penuh / +1 Hari)" if (is_overnight and et_obj == st_obj) else (" (Lewat Tengah Malam / +1 Hari)" if is_overnight else "")
        Notification.objects.create(
            user=user,
            type='booking_pending',
            title='Booking Berhasil Dibuat',
            message=f'Booking Anda untuk {booking.room.name} ({duration_hours} jam{overnight_info}, Rp {int(total_price):,}) sedang menunggu persetujuan.',
            booking=booking
        )

        return BookingDetailSerializer(booking, context=context).data

    def _booking_get_my_bookings(self, params, user, context):
        self._require_auth(user)
        bookings = Booking.objects.filter(user=user).order_by('-created_at')

        # Auto-create missing invoices for approved bookings
        for b in bookings:
            if b.status in ['approved', 'completed'] and not hasattr(b, 'invoice'):
                amount = b.total_price
                tax = amount * Decimal('0.11')
                Invoice.objects.create(
                    booking=b,
                    amount=amount,
                    tax=tax,
                    total=amount + tax,
                    description=f'Booking {b.room.name} ({b.booking_date})'
                )

        bookings = Booking.objects.filter(user=user).order_by('-created_at')
        return BookingDetailSerializer(bookings, many=True, context=context).data

    def _booking_get_detail(self, params, user, context):
        booking_id = params.get('id') or params.get('booking_id')
        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            raise JSONRPCError(-32602, f"Booking {booking_id} not found")

        # Auto generate invoice if approved
        if booking.status in ['approved', 'completed'] and not hasattr(booking, 'invoice'):
            amount = booking.total_price
            tax = amount * Decimal('0.11')
            Invoice.objects.create(
                booking=booking,
                amount=amount,
                tax=tax,
                total=amount + tax,
                description=f'Booking {booking.room.name} ({booking.booking_date})'
            )
            booking.refresh_from_db()

        return BookingDetailSerializer(booking, context=context).data

    def _booking_cancel(self, params, user, context):
        self._require_auth(user)
        booking_id = params.get('id') or params.get('booking_id')
        try:
            booking = Booking.objects.get(id=booking_id, user=user)
        except Booking.DoesNotExist:
            raise JSONRPCError(-32602, "Booking tidak ditemukan")

        if booking.status in ['completed', 'cancelled']:
            raise JSONRPCError(-32602, "Booking tidak dapat dibatalkan")

        booking.status = 'cancelled'
        booking.save()

        if hasattr(booking, 'payment'):
            booking.payment.status = 'refunded'
            booking.payment.save()

        Notification.objects.create(
            user=booking.user,
            type='booking_cancelled',
            title='Booking Dibatalkan',
            message=f'Booking Anda untuk {booking.room.name} telah dibatalkan.',
            booking=booking
        )

        return {'message': 'Booking berhasil dibatalkan'}

    def _payment_submit(self, params, user, context):
        self._require_auth(user)
        booking_id = params.get('booking_id') or params.get('booking')
        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            raise JSONRPCError(-32602, "Booking tidak ditemukan")

        payment, _ = Payment.objects.get_or_create(
            booking=booking,
            defaults={
                'amount': booking.total_price,
                'method': params.get('method', 'transfer'),
                'status': 'pending'
            }
        )

        # Handle proof upload via base64
        proof_base64 = params.get('proof_base64')
        if proof_base64:
            try:
                format, imgstr = proof_base64.split(';base64,') if ';base64,' in proof_base64 else (None, proof_base64)
                ext = format.split('/')[-1] if format else 'jpg'
                file_name = f"payment_proof_{booking.id}_{int(datetime.now().timestamp())}.{ext}"
                payment.proof = ContentFile(base64.b64decode(imgstr), name=file_name)
            except Exception:
                pass
        payment.status = 'pending'
        payment.save()

        Notification.objects.create(
            user=booking.user,
            type='payment_reminder',
            title='Pembayaran Diterima',
            message=f'Pembayaran untuk booking {booking.booking_code} telah diterima dan sedang menunggu verifikasi.',
            booking=booking
        )

        return PaymentSerializer(payment, context=context).data

    def _invoice_get_detail(self, params, user, context):
        invoice_id = params.get('id') or params.get('invoice_id')
        booking_id = params.get('booking_id')
        if invoice_id:
            invoice = Invoice.objects.filter(id=invoice_id).first()
        elif booking_id:
            invoice = Invoice.objects.filter(booking_id=booking_id).first()
        else:
            raise JSONRPCError(-32602, "Mohon sertakan id atau booking_id")

        if not invoice:
            raise JSONRPCError(-32602, "Invoice tidak ditemukan")

        return InvoiceSerializer(invoice, context=context).data

    def _review_get_list(self, params, user, context):
        room_id = params.get('room') or params.get('room_id')
        reviews = Review.objects.all().order_by('-created_at')
        if room_id:
            reviews = reviews.filter(room_id=room_id)
        return ReviewSerializer(reviews, many=True, context=context).data

    def _review_create(self, params, user, context):
        self._require_auth(user)
        room_id = params.get('room') or params.get('room_id')
        rating = params.get('rating')
        comment = params.get('comment', '')
        booking_id = params.get('booking') or params.get('booking_id')

        try:
            room = Room.objects.get(id=room_id)
        except Room.DoesNotExist:
            raise JSONRPCError(-32602, "Room tidak ditemukan")

        review = Review.objects.create(
            user=user,
            room=room,
            booking_id=booking_id if booking_id else None,
            rating=rating,
            comment=comment
        )
        return ReviewSerializer(review, context=context).data

    def _notification_get_unread_count(self, params, user, context):
        self._require_auth(user)
        count = Notification.objects.filter(user=user, is_read=False).count()
        return {'unread_count': count}

    def _notification_get_list(self, params, user, context):
        self._require_auth(user)
        notifs = Notification.objects.filter(user=user).order_by('-created_at')
        return NotificationSerializer(notifs, many=True, context=context).data

    def _notification_mark_as_read(self, params, user, context):
        self._require_auth(user)
        notif_id = params.get('id')
        try:
            notif = Notification.objects.get(id=notif_id, user=user)
            notif.is_read = True
            notif.read_at = datetime.now()
            notif.save()
            return {'message': 'Notifikasi ditandai sudah dibaca'}
        except Notification.DoesNotExist:
            raise JSONRPCError(-32602, "Notifikasi tidak ditemukan")

    def _notification_mark_all_as_read(self, params, user, context):
        self._require_auth(user)
        Notification.objects.filter(user=user, is_read=False).update(
            is_read=True,
            read_at=datetime.now()
        )
        return {'message': 'Semua notifikasi ditandai sudah dibaca'}

    # ================= Master Dispatch Method =================

    def dispatch(self, raw_body, request_meta=None, request_obj=None):
        request_meta = request_meta or {}
        req_id = None

        try:
            if isinstance(raw_body, bytes):
                raw_body = raw_body.decode('utf-8')
            if isinstance(raw_body, str):
                data = json.loads(raw_body)
            else:
                data = raw_body
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": "Parse error: Invalid JSON"},
                "id": None
            }

        # Check JSON-RPC 2.0 structure
        if not isinstance(data, dict) or data.get('jsonrpc') != '2.0' or 'method' not in data:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32600, "message": "Invalid Request: Must be JSON-RPC 2.0 with 'method' and 'jsonrpc'"},
                "id": data.get('id') if isinstance(data, dict) else None
            }

        req_id = data.get('id')
        method_name = data.get('method')
        params = data.get('params', {}) or {}

        if method_name not in self.registry:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Procedure '{method_name}' not found"},
                "id": req_id
            }

        user = self._extract_auth_user(request_meta, params)
        context = {'request': request_obj} if request_obj else {}

        try:
            procedure = self.registry[method_name]
            result = procedure(params, user, context)
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": req_id
            }
        except JSONRPCError as err:
            return {
                "jsonrpc": "2.0",
                "error": {"code": err.code, "message": err.message, "data": err.data},
                "id": req_id
            }
        except Exception as err:
            import traceback
            traceback.print_exc()
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": f"Internal RPC error: {str(err)}"},
                "id": req_id
            }


# Singleton dispatcher
rpc_dispatcher = RPCDispatcher()
