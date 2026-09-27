from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from rest_framework import permissions, status, filters
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiResponse
from .models import Booking
from .serializers import BookingSerializer, BookingCreateSerializer


class BookingListCreateView(APIView):
    """
    API view for listing and creating diagnostic test bookings.
    Patients can list their own bookings; Admins can view all bookings.
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['booking_reference', 'centre_test__centre__name', 'centre_test__test__name']
    ordering_fields = ['appointment_datetime', 'created_at', 'amount']

    def get_queryset(self):
        user = self.request.user
        queryset = Booking.objects.select_related(
            'user',
            'centre_test__centre',
            'centre_test__test'
        )
        if user.is_admin:
            return queryset.all()
        return queryset.filter(user=user)

    def filter_queryset(self, queryset):
        for backend in self.filter_backends:
            queryset = backend().filter_queryset(self.request, queryset, self)
        return queryset

    @extend_schema(
        summary="List user diagnostic test bookings",
        tags=["Bookings"],
        responses={200: BookingSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            serializer = BookingSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        serializer = BookingSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Book a new diagnostic test",
        tags=["Bookings"],
        request=BookingCreateSerializer,
        responses={201: BookingSerializer}
    )
    def post(self, request, *args, **kwargs):
        serializer = BookingCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()
        response_serializer = BookingSerializer(booking)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class BookingDetailView(APIView):
    """
    API view to retrieve, update, or delete a booking.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, pk):
        try:
            booking = Booking.objects.select_related(
                'user',
                'centre_test__centre',
                'centre_test__test'
            ).get(id=pk)
        except (Booking.DoesNotExist, ValueError):
            return None

        if not self.request.user.is_admin and booking.user != self.request.user:
            return "FORBIDDEN"
        return booking

    @extend_schema(summary="Get booking details", tags=["Bookings"], responses={200: BookingSerializer})
    def get(self, request, pk, *args, **kwargs):
        booking = self.get_object(pk)
        if booking is None:
            return Response({"error": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)
        if booking == "FORBIDDEN":
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        serializer = BookingSerializer(booking)
        return Response(serializer.data)

    @extend_schema(summary="Update booking details", tags=["Bookings"], request=BookingSerializer, responses={200: BookingSerializer})
    def put(self, request, pk, *args, **kwargs):
        booking = self.get_object(pk)
        if booking is None:
            return Response({"error": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)
        if booking == "FORBIDDEN":
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        serializer = BookingSerializer(booking, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(summary="Partially update booking details", tags=["Bookings"], request=BookingSerializer, responses={200: BookingSerializer})
    def patch(self, request, pk, *args, **kwargs):
        booking = self.get_object(pk)
        if booking is None:
            return Response({"error": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)
        if booking == "FORBIDDEN":
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        serializer = BookingSerializer(booking, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(summary="Delete a booking", tags=["Bookings"], responses={204: None})
    def delete(self, request, pk, *args, **kwargs):
        booking = self.get_object(pk)
        if booking is None:
            return Response({"error": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)
        if booking == "FORBIDDEN":
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        booking.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BookingCancelView(APIView):
    """
    Cancel a booking. Allowed if booking is in PENDING or CONFIRMED state.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Cancel an existing booking",
        tags=["Bookings"],
        responses={
            200: OpenApiResponse(description="Booking cancelled successfully"),
            400: OpenApiResponse(description="Cannot cancel booking in current state"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Booking not found"),
        }
    )
    def post(self, request, pk, *args, **kwargs):
        try:
            booking = Booking.objects.get(id=pk)
        except (Booking.DoesNotExist, ValueError):
            return Response({"error": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)

        if not request.user.is_admin and booking.user != request.user:
            return Response({"error": "You do not have permission to cancel this booking."}, status=status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            booking = Booking.objects.select_for_update().get(id=booking.id)

            if booking.status == Booking.Status.CANCELLED:
                return Response(
                    {"error": "Booking is already cancelled."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if booking.status == Booking.Status.FAILED:
                return Response(
                    {"error": "Cannot cancel a failed booking."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            booking.status = Booking.Status.CANCELLED
            booking.save()

        return Response(
            {
                "message": f"Booking {booking.booking_reference} cancelled successfully.",
                "booking": BookingSerializer(booking).data
            },
            status=status.HTTP_200_OK
        )
