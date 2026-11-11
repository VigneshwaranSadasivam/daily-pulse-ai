from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm

from .forms import RegisterForm
from .models import UserPreference


def register(request):

    if request.method == "POST":

        form = RegisterForm(request.POST)

        if form.is_valid():

            user = form.save()

            UserPreference.objects.get_or_create(
                user=user
            )

            login(request, user)

            return redirect("dashboard")

    else:
        form = RegisterForm()

    return render(
        request,
        "accounts/register.html",
        {"form": form}
    )


def user_login(request):

    if request.method == "POST":

        form = AuthenticationForm(
            request,
            data=request.POST
        )

        form.fields["username"].label = "Email"
        form.fields["username"].widget.attrs.update({
            "class": "form-control",
            "type": "email"
        })

        if form.is_valid():

            login(request, form.get_user())

            return redirect("dashboard")

    else:
        form = AuthenticationForm(request)

        form.fields["username"].label = "Email"
        form.fields["username"].widget.attrs.update({
            "class": "form-control",
            "type": "email"
        })

    return render(
        request,
        "accounts/login.html",
        {"form": form}
    )