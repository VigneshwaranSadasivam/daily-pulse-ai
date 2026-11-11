from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from interests.models import Interest, Tag


@login_required
def dashboard(request):

    interests = Interest.objects.filter(
        user=request.user
    )

    tags = Tag.objects.filter(
        user=request.user
    )

    context = {
        "total_interests": interests.count(),
        "total_tags": tags.count(),
        "active_interests": interests.filter(
            is_active=True
        ).count(),
        "active_tags": tags.filter(
            is_active=True
        ).count(),
    }

    return render(
        request,
        "dashboard/index.html",
        context
    )