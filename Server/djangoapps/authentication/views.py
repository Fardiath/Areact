from django.shortcuts import render
from rest_framework import generics, status, views
from .serializers import RegisterSerializer, EmailVerificationSerializer, LoginSerializer, ResetPasswordEmailRequestSerializer, SetNewPasswordSerializer
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User
from .utils import Util
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
import jwt
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .renderers import UserRenderer
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import smart_str, force_str, smart_bytes, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.core.mail import send_mail
from django.shortcuts import redirect
from django.http import HttpResponsePermanentRedirect
import os


class CustomRedirect(HttpResponsePermanentRedirect):
    allowed_schemes = [os.environ.get('APP_SCHEME'), 'http', 'https']


# Create your views here.
# Renderer est une composante responsable de l'affichage d'un contenu dans le navigateur

class RegisterView(generics.GenericAPIView):

    serializer_class=RegisterSerializer
    renderer_classes = (UserRenderer,)

    def post(self, request):
        user = request.data
        print(user)
        serializer=self.serializer_class(data=user)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        user_data = serializer.data
        user = User.objects.get(email=user_data['email'])

        token = RefreshToken.for_user(user).access_token
        current_site = get_current_site(request).domain
        relativeLink = reverse('email-verify')
        absurl = 'http://'+current_site+relativeLink+"?token="+str(token)
        email_body = 'Hi ' +user.username+ 'Use link below to verify your email \n' + absurl
        data = {'email_body': email_body, 'to_email': user.email, 
                 'email_subject': 'Verify your email'}
        
        send_mail(
                'Reset your password',
                email_body,
                settings.EMAIL_HOST_USER,
                [user.email],
                fail_silently=False,
            )        
        return Response(user_data, status=status.HTTP_201_CREATED)
    
class VerifyEmail(views.APIView):
    serializer_class = EmailVerificationSerializer
    token_param_config = openapi.Parameter('token', in_ = openapi.IN_QUERY, description='description', type = openapi.TYPE_STRING)
    @swagger_auto_schema(manual_parameters=[token_param_config])

    def get(self, request):
        token = request.GET.get('token')
        try:
            payload = jwt.decode(token, settings.SECRET_KEY)
            user = User.objects.get(id=payload['user_id'])
            if not user.is_verified:
                user.is_verified = True
                user.save()
            return Response({'email': 'Is activated successfully'}, status=status.HTTP_200_OK)

        except jwt.ExpiredSignatureError as identifier:
            return Response({'error':'Activation Expired'}, status=status.HTTP_400_BAD_REQUEST)
        
        except jwt.exceptions.DecodeError as identifier:
            return Response({'error':'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)
        
class LoginAPIView(generics.GenericAPIView):
    serializer_class=LoginSerializer
    def post(self, request):
        serializer = self.serializer_class(data = request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class RequestPasswordResetEmail(generics.GenericAPIView):
    serializer_class = ResetPasswordEmailRequestSerializer()

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        email = request.data['email']
        if User.objects.filter(email=email).exists():
                user = User.objects.get(email=email)
                uidb64 = urlsafe_base64_encode(user.id)
                token = PasswordResetTokenGenerator().make_token(user)
                current_site = get_current_site(
                    request=request).domain
                relativeLink = reverse('password-reset-confirm', kwargs={'uidb64': uidb64, 'token': token})
               
                redirect_url = request.data.get('redirect_url', '')
                absurl = 'http://'+current_site+relativeLink
                email_body = 'Hello, \n Use link below to reset your password \n' + absurl + "?redirect_url=" + redirect_url,
                data = {'email_body': email_body, 'to_email': user.email, 
                'email_subject': 'Reset your password'}
                Util.send_email(data)
        return Response({'success': 'We have sent you a link to reset your password'}, status=status.HTTP_200_OK)

class PasswordTokenCheckAPI(generics.GenericAPIView):
    serializer_class = SetNewPasswordSerializer
    def get(self, request, uidb64, token):
        redirect_url = request.Get.get('redirect_url')
        try:
            id = smart_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(id = id)

            if not PasswordResetTokenGenerator().check_token(user, token):

                if len(redirect_url() > 3):
                    return CustomRedirect(redirect_url+'?token_valid=False')
                else:
                    return CustomRedirect(os.environ.get('FRONT_END_URL', '')+'?token_valid=False')

            if redirect_url and len(redirect_url() > 3):
                return CustomRedirect(redirect_url+'?token_valid=True&?message=Credential Valid&?uidb64='+uidb64+'&?token='+token)
            else:
                return CustomRedirect(os.environ.get('FRONT_END_URL', '')+'?token_valid=False')

        except DjangoUnicodeDecodeError as identifier:
            if not PasswordResetTokenGenerator().check_token(user):
                return CustomRedirect(redirect_url+'?token_valid=False')

class SetNewPasswordAPIView(generics.GenericAPIView):
    serializer_class = SetNewPasswordSerializer

    def patch(self, request):
        serializer = self.serializer_class(data=request.data)

        serializer.is_active(raise_exception=True)
        return Response({'success':True, 'message': 'Password is reset successfully'}, status=status.HTTP_200_OK)

