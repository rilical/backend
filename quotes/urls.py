from django.urls import path
from .views import QuoteAPIView

app_name = 'quotes'

urlpatterns = [
    path('', QuoteAPIView.as_view(), name='quotes-api'),
] 