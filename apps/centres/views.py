from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from rest_framework import filters, permissions, status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiResponse
from .models import DiagnosticCentre, DiagnosticTest, CentreTest
from .serializers import (
    DiagnosticCentreSerializer,
    DiagnosticTestSerializer,
    CentreTestSerializer,
    CentreTestCreateUpdateSerializer
)
from django.core.cache import cache
from .permissions import IsAdminOrReadOnly
from .services import (
    invalidate_centres_cache,
    invalidate_tests_cache,
    CACHE_KEY_CENTRES_LIST,
    CACHE_KEY_TESTS_LIST,
    CACHE_TIMEOUT
)


class DiagnosticCentreListCreateView(APIView):
    """
    API endpoint to list diagnostic centres or create a new diagnostic centre (Admin).
    """
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['city', 'is_active']
    search_fields = ['name', 'location', 'city', 'address']
    ordering_fields = ['name', 'created_at']

    def get_queryset(self):
        return DiagnosticCentre.objects.prefetch_related('offered_tests__test').all()

    def filter_queryset(self, queryset):
        for backend in self.filter_backends:
            queryset = backend().filter_queryset(self.request, queryset, self)
        return queryset

    @extend_schema(summary="List all diagnostic centres", tags=["Centres & Tests"], responses={200: DiagnosticCentreSerializer(many=True)})
    def get(self, request, *args, **kwargs):
        is_unfiltered = not request.query_params
        if is_unfiltered:
            cached_data = cache.get(CACHE_KEY_CENTRES_LIST)
            if cached_data is not None:
                return Response(cached_data)

        queryset = self.filter_queryset(self.get_queryset())
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            serializer = DiagnosticCentreSerializer(page, many=True)
            response = paginator.get_paginated_response(serializer.data)
            if is_unfiltered:
                cache.set(CACHE_KEY_CENTRES_LIST, response.data, timeout=CACHE_TIMEOUT)
            return response
        serializer = DiagnosticCentreSerializer(queryset, many=True)
        if is_unfiltered:
            cache.set(CACHE_KEY_CENTRES_LIST, serializer.data, timeout=CACHE_TIMEOUT)
        return Response(serializer.data)

    @extend_schema(summary="Create a new diagnostic centre (Admin)", tags=["Centres & Tests"], request=DiagnosticCentreSerializer, responses={201: DiagnosticCentreSerializer})
    def post(self, request, *args, **kwargs):
        serializer = DiagnosticCentreSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        centre = serializer.save()
        invalidate_centres_cache()
        return Response(DiagnosticCentreSerializer(centre).data, status=status.HTTP_201_CREATED)


class DiagnosticCentreDetailView(APIView):
    """
    API endpoint to retrieve, update, or delete a diagnostic centre.
    """
    permission_classes = [IsAdminOrReadOnly]

    def get_object(self, pk):
        try:
            return DiagnosticCentre.objects.prefetch_related('offered_tests__test').get(id=pk)
        except (DiagnosticCentre.DoesNotExist, ValueError):
            return None

    @extend_schema(summary="Retrieve a diagnostic centre detail", tags=["Centres & Tests"], responses={200: DiagnosticCentreSerializer})
    def get(self, request, pk, *args, **kwargs):
        centre = self.get_object(pk)
        if centre is None:
            return Response({"error": "Diagnostic centre not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = DiagnosticCentreSerializer(centre)
        return Response(serializer.data)

    @extend_schema(summary="Update a diagnostic centre (Admin)", tags=["Centres & Tests"], request=DiagnosticCentreSerializer, responses={200: DiagnosticCentreSerializer})
    def put(self, request, pk, *args, **kwargs):
        centre = self.get_object(pk)
        if centre is None:
            return Response({"error": "Diagnostic centre not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = DiagnosticCentreSerializer(centre, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        invalidate_centres_cache()
        return Response(serializer.data)

    @extend_schema(summary="Partially update a diagnostic centre (Admin)", tags=["Centres & Tests"], request=DiagnosticCentreSerializer, responses={200: DiagnosticCentreSerializer})
    def patch(self, request, pk, *args, **kwargs):
        centre = self.get_object(pk)
        if centre is None:
            return Response({"error": "Diagnostic centre not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = DiagnosticCentreSerializer(centre, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        invalidate_centres_cache()
        return Response(serializer.data)

    @extend_schema(summary="Delete a diagnostic centre (Admin)", tags=["Centres & Tests"], responses={204: None})
    def delete(self, request, pk, *args, **kwargs):
        centre = self.get_object(pk)
        if centre is None:
            return Response({"error": "Diagnostic centre not found."}, status=status.HTTP_404_NOT_FOUND)
        centre.delete()
        invalidate_centres_cache()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DiagnosticTestListCreateView(APIView):
    """
    API endpoint to list diagnostic tests or create a new diagnostic test (Admin).
    """
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category']
    search_fields = ['name', 'code', 'category', 'description']
    ordering_fields = ['name', 'code', 'category']

    def get_queryset(self):
        return DiagnosticTest.objects.all()

    def filter_queryset(self, queryset):
        for backend in self.filter_backends:
            queryset = backend().filter_queryset(self.request, queryset, self)
        return queryset

    @extend_schema(summary="List all diagnostic tests", tags=["Centres & Tests"], responses={200: DiagnosticTestSerializer(many=True)})
    def get(self, request, *args, **kwargs):
        is_unfiltered = not request.query_params
        if is_unfiltered:
            cached_data = cache.get(CACHE_KEY_TESTS_LIST)
            if cached_data is not None:
                return Response(cached_data)

        queryset = self.filter_queryset(self.get_queryset())
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            serializer = DiagnosticTestSerializer(page, many=True)
            response = paginator.get_paginated_response(serializer.data)
            if is_unfiltered:
                cache.set(CACHE_KEY_TESTS_LIST, response.data, timeout=CACHE_TIMEOUT)
            return response
        serializer = DiagnosticTestSerializer(queryset, many=True)
        if is_unfiltered:
            cache.set(CACHE_KEY_TESTS_LIST, serializer.data, timeout=CACHE_TIMEOUT)
        return Response(serializer.data)

    @extend_schema(summary="Create a new diagnostic test (Admin)", tags=["Centres & Tests"], request=DiagnosticTestSerializer, responses={201: DiagnosticTestSerializer})
    def post(self, request, *args, **kwargs):
        serializer = DiagnosticTestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        test = serializer.save()
        invalidate_tests_cache()
        return Response(DiagnosticTestSerializer(test).data, status=status.HTTP_201_CREATED)


class DiagnosticTestDetailView(APIView):
    """
    API endpoint to retrieve, update, or delete a diagnostic test.
    """
    permission_classes = [IsAdminOrReadOnly]

    def get_object(self, pk):
        try:
            return DiagnosticTest.objects.get(id=pk)
        except (DiagnosticTest.DoesNotExist, ValueError):
            return None

    @extend_schema(summary="Retrieve a diagnostic test detail", tags=["Centres & Tests"], responses={200: DiagnosticTestSerializer})
    def get(self, request, pk, *args, **kwargs):
        test = self.get_object(pk)
        if test is None:
            return Response({"error": "Diagnostic test not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = DiagnosticTestSerializer(test)
        return Response(serializer.data)

    @extend_schema(summary="Update a diagnostic test (Admin)", tags=["Centres & Tests"], request=DiagnosticTestSerializer, responses={200: DiagnosticTestSerializer})
    def put(self, request, pk, *args, **kwargs):
        test = self.get_object(pk)
        if test is None:
            return Response({"error": "Diagnostic test not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = DiagnosticTestSerializer(test, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        invalidate_tests_cache()
        return Response(serializer.data)

    @extend_schema(summary="Partially update a diagnostic test (Admin)", tags=["Centres & Tests"], request=DiagnosticTestSerializer, responses={200: DiagnosticTestSerializer})
    def patch(self, request, pk, *args, **kwargs):
        test = self.get_object(pk)
        if test is None:
            return Response({"error": "Diagnostic test not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = DiagnosticTestSerializer(test, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        invalidate_tests_cache()
        return Response(serializer.data)

    @extend_schema(summary="Delete a diagnostic test (Admin)", tags=["Centres & Tests"], responses={204: None})
    def delete(self, request, pk, *args, **kwargs):
        test = self.get_object(pk)
        if test is None:
            return Response({"error": "Diagnostic test not found."}, status=status.HTTP_404_NOT_FOUND)
        test.delete()
        invalidate_tests_cache()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CentreTestListCreateView(APIView):
    """
    API endpoint to list centre test offerings or assign a test to a centre (Admin).
    """
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['centre', 'test', 'is_available']
    search_fields = ['centre__name', 'centre__location', 'test__name', 'test__code']
    ordering_fields = ['price', 'created_at']

    def get_queryset(self):
        return CentreTest.objects.select_related('centre', 'test').all()

    def filter_queryset(self, queryset):
        for backend in self.filter_backends:
            queryset = backend().filter_queryset(self.request, queryset, self)
        return queryset

    @extend_schema(summary="List centre test offerings & prices", tags=["Centres & Tests"], responses={200: CentreTestSerializer(many=True)})
    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            serializer = CentreTestSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        serializer = CentreTestSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(summary="Assign a test to a centre with price (Admin)", tags=["Centres & Tests"], request=CentreTestCreateUpdateSerializer, responses={201: CentreTestSerializer})
    def post(self, request, *args, **kwargs):
        serializer = CentreTestCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        centre_test = serializer.save()
        invalidate_centres_cache()
        return Response(CentreTestSerializer(centre_test).data, status=status.HTTP_201_CREATED)


class CentreTestDetailView(APIView):
    """
    API endpoint to retrieve, update, or remove a centre test offering.
    """
    permission_classes = [IsAdminOrReadOnly]

    def get_object(self, pk):
        try:
            return CentreTest.objects.select_related('centre', 'test').get(id=pk)
        except (CentreTest.DoesNotExist, ValueError):
            return None

    @extend_schema(summary="Retrieve a centre test price detail", tags=["Centres & Tests"], responses={200: CentreTestSerializer})
    def get(self, request, pk, *args, **kwargs):
        centre_test = self.get_object(pk)
        if centre_test is None:
            return Response({"error": "Centre test offering not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = CentreTestSerializer(centre_test)
        return Response(serializer.data)

    @extend_schema(summary="Update centre test pricing/availability (Admin)", tags=["Centres & Tests"], request=CentreTestCreateUpdateSerializer, responses={200: CentreTestSerializer})
    def put(self, request, pk, *args, **kwargs):
        centre_test = self.get_object(pk)
        if centre_test is None:
            return Response({"error": "Centre test offering not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = CentreTestCreateUpdateSerializer(centre_test, data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        invalidate_centres_cache()
        return Response(CentreTestSerializer(updated).data)

    @extend_schema(summary="Partially update centre test pricing/availability (Admin)", tags=["Centres & Tests"], request=CentreTestCreateUpdateSerializer, responses={200: CentreTestSerializer})
    def patch(self, request, pk, *args, **kwargs):
        centre_test = self.get_object(pk)
        if centre_test is None:
            return Response({"error": "Centre test offering not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = CentreTestCreateUpdateSerializer(centre_test, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        invalidate_centres_cache()
        return Response(CentreTestSerializer(updated).data)

    @extend_schema(summary="Remove a test from a centre (Admin)", tags=["Centres & Tests"], responses={204: None})
    def delete(self, request, pk, *args, **kwargs):
        centre_test = self.get_object(pk)
        if centre_test is None:
            return Response({"error": "Centre test offering not found."}, status=status.HTTP_404_NOT_FOUND)
        centre_test.delete()
        invalidate_centres_cache()
        return Response(status=status.HTTP_204_NO_CONTENT)
