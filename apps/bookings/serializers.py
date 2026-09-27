from rest_framework import serializers
from django.utils import timezone
from apps.centres.models import CentreTest, DiagnosticCentre, DiagnosticTest
from apps.authentication.serializers import UserSerializer
from .models import Booking


class BookingSerializer(serializers.ModelSerializer):
    patient = UserSerializer(source='user', read_only=True)
    centre_name = serializers.CharField(source='centre.name', read_only=True)
    centre_location = serializers.CharField(source='centre.location', read_only=True)
    test_name = serializers.CharField(source='test.name', read_only=True)
    test_code = serializers.CharField(source='test.code', read_only=True)

    class Meta:
        model = Booking
        fields = (
            'id',
            'booking_reference',
            'patient',
            'centre_test',
            'centre_name',
            'centre_location',
            'test_name',
            'test_code',
            'appointment_datetime',
            'amount',
            'status',
            'notes',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'booking_reference',
            'patient',
            'amount',
            'status',
            'created_at',
            'updated_at',
        )


class BookingCreateSerializer(serializers.ModelSerializer):
    centre_id = serializers.UUIDField(write_only=True, required=False)
    test_id = serializers.UUIDField(write_only=True, required=False)
    centre_test = serializers.PrimaryKeyRelatedField(
        queryset=CentreTest.objects.select_related('centre', 'test').filter(is_available=True, centre__is_active=True),
        required=False
    )

    class Meta:
        model = Booking
        fields = (
            'id',
            'booking_reference',
            'centre_test',
            'centre_id',
            'test_id',
            'appointment_datetime',
            'notes',
        )
        read_only_fields = ('id', 'booking_reference')

    def validate(self, attrs):
        centre_test = attrs.get('centre_test')
        centre_id = attrs.get('centre_id')
        test_id = attrs.get('test_id')

        # If centre_id and test_id are passed directly, look up centre_test
        if not centre_test:
            if not centre_id or not test_id:
                raise serializers.ValidationError(
                    "Either 'centre_test' ID or both 'centre_id' and 'test_id' must be provided."
                )
            try:
                centre_test = CentreTest.objects.get(
                    centre_id=centre_id,
                    test_id=test_id,
                    is_available=True,
                    centre__is_active=True
                )
                attrs['centre_test'] = centre_test
            except CentreTest.DoesNotExist:
                raise serializers.ValidationError(
                    "The selected diagnostic test is either not offered, unavailable, or the centre is inactive."
                )

        appointment_dt = attrs.get('appointment_datetime')
        if appointment_dt and appointment_dt <= timezone.now():
            raise serializers.ValidationError(
                {"appointment_datetime": "Appointment date and time must be in the future."}
            )

        return attrs

    def create(self, validated_data):
        validated_data.pop('centre_id', None)
        validated_data.pop('test_id', None)
        user = self.context['request'].user
        centre_test = validated_data['centre_test']
        
        booking = Booking.objects.create(
            user=user,
            centre_test=centre_test,
            amount=centre_test.price,
            appointment_datetime=validated_data['appointment_datetime'],
            notes=validated_data.get('notes', ''),
            status=Booking.Status.PENDING
        )
        return booking
