from rest_framework import serializers
from .models import DiagnosticCentre, DiagnosticTest, CentreTest


class DiagnosticTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiagnosticTest
        fields = ('id', 'name', 'code', 'category', 'description', 'preparation_instructions', 'created_at')
        read_only_fields = ('id', 'created_at')


class CentreTestSerializer(serializers.ModelSerializer):
    test_detail = DiagnosticTestSerializer(source='test', read_only=True)
    centre_name = serializers.CharField(source='centre.name', read_only=True)
    centre_location = serializers.CharField(source='centre.location', read_only=True)

    class Meta:
        model = CentreTest
        fields = (
            'id',
            'centre',
            'centre_name',
            'centre_location',
            'test',
            'test_detail',
            'price',
            'is_available',
            'estimated_hours',
            'created_at'
        )
        read_only_fields = ('id', 'created_at')


class CentreTestCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CentreTest
        fields = ('id', 'centre', 'test', 'price', 'is_available', 'estimated_hours')

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero.")
        return value


class DiagnosticCentreSerializer(serializers.ModelSerializer):
    offered_tests = CentreTestSerializer(many=True, read_only=True)
    total_tests = serializers.SerializerMethodField()

    class Meta:
        model = DiagnosticCentre
        fields = (
            'id',
            'name',
            'location',
            'address',
            'city',
            'contact_phone',
            'contact_email',
            'is_active',
            'total_tests',
            'offered_tests',
            'created_at'
        )
        read_only_fields = ('id', 'created_at')

    def get_total_tests(self, obj):
        return obj.offered_tests.filter(is_available=True).count()
