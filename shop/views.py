from django.shortcuts import render, get_object_or_404, redirect
from shop.models.products import Product, Category
from django.db.models.functions import Coalesce
from django.db.models import DecimalField
from shop.models.orders import Order
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from shop.models.order_items import OrderItem
from shop.models.cancel_order import CancelOrder
from shop.forms import CancelOrderForm
from shop.models.reports import Report
from django.db.models import Sum
from django.contrib import messages
from datetime import datetime, time
from django.utils import timezone
import json

# Create your views here.


def home(request):
    today = timezone.localdate()

    start_datetime = datetime.combine(today, time.min).replace(
        tzinfo=timezone.get_current_timezone()
    )
    end_datetime = datetime.combine(today, time.max).replace(
        tzinfo=timezone.get_current_timezone()
    )

    today_orders = Order.objects.filter(
        status="success",
        is_canceled=False,
        created_at__range=(start_datetime, end_datetime),
    )
    canceled_order = Order.objects.filter(
        is_canceled=True, created_at__range=(start_datetime, end_datetime)
    ).count()

    total_sales = today_orders.aggregate(
        total=Coalesce(Sum("total_price"), 0, output_field=DecimalField())
    )["total"]

    order_count = today_orders.count()

    average_order_value = total_sales / order_count if order_count > 0 else 0

    products = Product.objects.all()
    categories = Category.objects.all()
    orders = Order.objects.all()
    reasons = CancelOrder.objects.all()
    form = CancelOrderForm()

    if "category" in request.GET:
        category = request.GET.get("category")
        if category and category != "All Product":
            products = products.filter(category__name=category)

        products_data = [
            {
                "name": product.name,
                "selling_price": product.selling_price,
                "stock_quantity": product.stock_quantity,
                "status": product.status,
                "category": product.category.name if product.category else "",
            }
            for product in products
        ]
        return JsonResponse({"products": products_data})

    if request.method == "POST":
        product_name = request.POST["name"]

        products = Product.objects.filter(name__icontains=product_name)

    context = {
        "products": products,
        "categories": categories,
        "orders": orders,
        "reasons": reasons,
        "form": form,
        "total_sales": float(total_sales) or 0.00,
        "order_count": order_count or 0,
        "average_order_value": float(average_order_value) or 0.00,
        "canceled_order": canceled_order or 0,
    }
    return render(request, "main/home.html", context)


@csrf_exempt
def add_to_order(request, product_id):
    try:
        product = Product.objects.get(id=product_id)

        order, created = Order.objects.get_or_create(
            status="pending", defaults={"total_price": 0}
        )

        order_item, created = OrderItem.objects.get_or_create(
            order=order, product=product, defaults={"quantity": 1}
        )

        if not created:
            order_item.quantity += 1
            order_item.save()

        return JsonResponse(
            {"success": True, "order_items": get_order_items_data(order)}
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@csrf_exempt
def update_order_item(request, item_id):
    try:
        data = json.loads(request.body)
        change = data.get("change", 0)

        order_item = OrderItem.objects.get(id=item_id)
        order_item.quantity += change

        if order_item.quantity <= 0:
            order_item.delete()
        else:
            order_item.save()

        return JsonResponse(
            {"success": True, "order_items": get_order_items_data(order_item.order)}
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@csrf_exempt
def complete_order(request):
    try:

        order = Order.objects.filter(status="pending").first()

        if not order or not order.items.exists():
            raise Exception("No active order to complete")

        order.status = "success"
        order.total_price = order.get_total_price()
        order.save()

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


def get_active_order(request):
    try:
        order = Order.objects.filter(status="pending").first()
        if order:
            return JsonResponse(
                {"success": True, "order_items": get_order_items_data(order)}
            )
        return JsonResponse({"success": True, "order_items": []})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


def get_recent_orders(request):
    try:
        orders = Order.objects.filter(status="success").order_by("-created_at")[:8]
        orders_data = [
            {
                "id": order.id,
                "order_id": order.order_id,
                "total_price": float(order.total_price),
                "status": order.status,
                "created_at": order.created_at.strftime("%Y-%m-%d %H:%M"),
                "item_count": order.items.count(),
            }
            for order in orders
        ]

        return JsonResponse({"success": True, "orders": orders_data})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


def get_order_items_data(order):
    return [
        {
            "id": item.id,
            "product_id": item.product.id,
            "product_name": item.product.name,
            "product_price": float(item.product.selling_price),
            "quantity": item.quantity,
        }
        for item in order.items.all()
    ]


def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    form = CancelOrderForm()

    if request.method == "POST":
        form = CancelOrderForm(request.POST)
        if form.is_valid():
            reason = form.cleaned_data["reason"]
            context = form.cleaned_data["context"]

            Report.objects.create(order=order, context=reason, dec=context)
            messages.success(request, "Order Canceled Successful")
            return redirect("home")
        messages = "an error occured canceling order"
        return messages
    context = {"form": form}
    return render(request, "main/home.html", context)


def products(request):
    products = Product.objects.all()

    context = {
        'products':products
    }
    return render(request, 'main/products.html', context)


def reports(request):
    reports = Report.objects.all()

    context = {
        'reports':reports
    }
    return render(request, 'main/products.html', context)

