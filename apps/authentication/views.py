from rest_framework.views import APIView
from rest_framework import status, permissions
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.contrib.auth import get_user_model
from .serializers import RegisterSerializer, UserSerializer, CustomTokenObtainPairSerializer

User = get_user_model()


class RegisterView(APIView):
    """
    Endpoint for new user registration.
    Allows patients or admins to sign up with username, email, and password.
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Authentication'],
        summary="Register a new user",
        request=RegisterSerializer,
        responses={
            201: OpenApiResponse(description="User registered successfully", response=UserSerializer),
            400: OpenApiResponse(description="Validation error"),
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "message": "User registered successfully.",
                "user": UserSerializer(user).data
            },
            status=status.HTTP_201_CREATED
        )


class CustomTokenObtainPairView(APIView):
    """
    Endpoint for user login. Returns JWT access token, refresh token, and user profile.
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Authentication'],
        summary="User login with JWT token pair",
        request=CustomTokenObtainPairSerializer,
        responses={
            200: OpenApiResponse(description="Token pair and user profile"),
            401: OpenApiResponse(description="Invalid credentials"),
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = CustomTokenObtainPairSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class UserProfileView(APIView):
    """
    Retrieve or update currently authenticated user's profile.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Authentication'],
        summary="Retrieve user profile",
        responses={200: UserSerializer}
    )
    def get(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['Authentication'],
        summary="Update user profile (full update)",
        request=UserSerializer,
        responses={200: UserSerializer}
    )
    def put(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['Authentication'],
        summary="Partially update user profile",
        request=UserSerializer,
        responses={200: UserSerializer}
    )
    def patch(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
