from django.urls import path
from shop.views import *


urlpatterns = [
    path('', home, name='home'),
    path('add-to-order/<int:product_id>/', add_to_order, name='add_to_order'),
    path('update-order-item/<int:item_id>/', update_order_item, name='update_order_item'),
    path('complete-order/', complete_order, name='complete_order'),
    path('get-active-order/', get_active_order, name='get_active_order'),
    path('get-recent-orders/', get_recent_orders, name='get_recent_orders'),
]