from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.conf import settings

import boto3


def send_email(email, subject, body_text):

    # Create boto3 SES client
    ses_client = boto3.client(
        "ses",
        aws_access_key_id=settings.SES_MOCAPSCHOOL_KEY,
        aws_secret_access_key=settings.SES_MOCAPSCHOOL_SECRET,
        region_name=settings.SES_MOCAPSCHOOL_REGION,
    )

    # Send email using AWS SES API
    ses_client.send_email(
        Source=settings.DEFAULT_FROM_EMAIL,
        Destination={
            "ToAddresses": [email],
        },
        Message={
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": {
                "Text": {"Data": body_text, "Charset": "UTF-8"},
            },
        },
    )


def send_new_account_email(user):

    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    template_name = "registration/activation_email.txt"
    confirm_url = request.build_absolute_uri(f"/activate/{uid}/{token}/")

    subject = "Confirm your account"
    body_text = render_to_string(template_name, {
        "user": user,
        "confirm_url": confirm_url,
    })

    send_email(user.email, subject, body_text)


def send_purchase_email(email, title):
    body_text = render_to_string("purchase_ok.txt", {'title': title})
    send_email(email, "Purchase ok", body_text)


def send_admin_email(subject, message):
    send_email("al@peeldev.com", subject, message)
