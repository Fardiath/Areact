from django.contrib.auth.models import(AbstractBaseUser, BaseUserManager, PermissionsMixin)

from django.db import models

class g_auth(AbstractBaseUser):
    id_token = ""
