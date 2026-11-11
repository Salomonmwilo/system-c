from django.urls import path

from . import views

app_name = "academy"

urlpatterns = [
    path("", views.AcademyHomeView.as_view(), name="home"),
    # Acheteur
    path("offers/", views.OfferListView.as_view(), name="offer_list"),
    path("offers/<int:pk>/", views.OfferDetailView.as_view(), name="offer_detail"),
    path("offers/<int:pk>/order/", views.OrderCreateView.as_view(), name="order_create"),
    path("my-orders/", views.MyOrderListView.as_view(), name="my_order_list"),
    path("my-orders/<int:pk>/", views.MyOrderDetailView.as_view(), name="my_order_detail"),
    path("my-orders/<int:pk>/cancel/", views.MyOrderCancelView.as_view(), name="my_order_cancel"),
    # Administration des commandes
    path("orders/", views.OrderListView.as_view(), name="order_list"),
    path("orders/<int:pk>/", views.OrderDetailView.as_view(), name="order_detail"),
    path("orders/<int:pk>/confirm/", views.OrderConfirmView.as_view(), name="order_confirm"),
    path("orders/<int:pk>/cancel/", views.OrderCancelView.as_view(), name="order_cancel"),
    path("orders/<int:pk>/refund/", views.OrderRefundView.as_view(), name="order_refund"),
]
