from django import forms
from .models import Interest


class InterestForm(forms.ModelForm):
    class Meta:
        model = Interest
        fields = ["name", "description"]

        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. Artificial Intelligence",
                "maxlength": "150",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "What specifically interests you?",
            }),
        }

    def clean_name(self):
        name = " ".join(
            self.cleaned_data["name"].strip().split()
        )

        if not name:
            raise forms.ValidationError(
                "Interest name cannot be empty."
            )

        normalized = name.casefold()

        existing = Interest.objects.filter(
            user=self.user,
            normalized_name=normalized,
        )

        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)

        if existing.exists():
            raise forms.ValidationError(
                "You already have an interest with this name."
            )

        return name

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user


class TagForm(forms.Form):
    name = forms.CharField(
        max_length=150,
        strip=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Enter a tag",
            "maxlength": "150",
        }),
    )

    def clean_name(self):
        name = " ".join(
            self.cleaned_data["name"].split()
        )

        if not name:
            raise forms.ValidationError(
                "Tag cannot be empty."
            )

        return name