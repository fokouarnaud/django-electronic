from django.urls import path

from . import views

app_name = "curriculum"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path(
        "chapters/<slug:chapter_slug>/concepts/<slug:concept_slug>/",
        views.ConceptDetailView.as_view(),
        name="concept_detail",
    ),
    path(
        "chapters/<slug:chapter_slug>/concepts/<slug:concept_slug>/quiz/",
        views.QuizView.as_view(),
        name="quiz",
    ),
]
