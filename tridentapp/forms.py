# forms.py
from django import forms
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.conf import settings
import boto3

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]


class SESEmailPasswordResetForm(PasswordResetForm):
    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        subject = self.render_mail(subject_template_name, context).strip()
        body = self.render_mail(email_template_name, context)

        ses_client = boto3.client(
            "ses",
            aws_access_key_id=settings.SES_MOCAPSCHOOL_KEY,
            aws_secret_access_key=settings.SES_MOCAPSCHOOL_SECRET,
            region_name=settings.SES_MOCAPSCHOOL_REGION,
        )

        ses_client.send_email(
            Source=settings.DEFAULT_FROM_EMAIL,
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Text": {"Data": body, "Charset": "UTF-8"},
                },
            },
        )